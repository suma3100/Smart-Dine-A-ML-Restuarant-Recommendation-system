"""Deterministic ranking with strict filters and feature-derived explanations."""
from pathlib import Path
import joblib
import warnings
import unicodedata
import numpy as np
import pandas as pd
from .paths import DATA_DIR, MODEL_PATH, METADATA_PATH
from .schema import FEATURES, VERSION, sha256
from .features import RestaurantFeatureBuilder
from .group_preferences import normalize_text
from .metadata import load_metadata
from sklearn.exceptions import InconsistentVersionWarning



def restaurant_display_name(name):
    """Repair reversible UTF-8 mis-decoding for display without editing source rows."""
    if pd.isna(name):
        return ''
    text = str(name).strip()
    for _ in range(8):
        if not any(marker in text for marker in ['\u00c3', '\u00c2', '\u00e2']):
            break
        repaired = None
        for encoding in ['latin1', 'cp1252']:
            try:
                candidate = text.encode(encoding).decode('utf-8')
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
            if candidate != text:
                repaired = candidate
                break
        if repaired is None:
            break
        text = repaired
    return text


def restaurant_name_key(name, restaurant_id):
    """Presentation diversity only; physical branch records remain untouched.

    Match names across case, spacing, punctuation, accents and Unicode width variants.
    Missing names keep separate IDs rather than merging unrelated unknowns.
    """
    text = unicodedata.normalize('NFKD', normalize_text(restaurant_display_name(name))).casefold()
    key = ''.join(character for character in text if character.isalnum())
    return ('name', key) if key else ('id', str(restaurant_id))


class SmartDineRecommender:
    def __init__(self, data_path=None, model_path=None, metadata_path=None):
        self.data_path = Path(data_path or DATA_DIR / 'restaurant_features.csv')
        self.model_path = Path(model_path or MODEL_PATH)
        self.metadata_path = Path(metadata_path) if metadata_path else self.model_path.with_name('model_metadata.json')
        if not self.data_path.is_file():
            raise FileNotFoundError('Restaurant features missing; run pipeline.py features with cleaned input.')
        if not self.model_path.is_file():
            raise FileNotFoundError('Model missing; run pipeline.py train after split.')
        self.builder = RestaurantFeatureBuilder(pd.read_csv(self.data_path))
        self.df = self.builder.df
        self.locations_list = self.builder.locations
        self._restaurant_ids = self.df.restaurant_id.astype(str).tolist()
        self._restaurant_name_keys = [restaurant_name_key(name, rid)
                                     for name, rid in zip(self.df['name'], self._restaurant_ids)]
        with warnings.catch_warnings():
            warnings.simplefilter('error', InconsistentVersionWarning)
            self.model = joblib.load(self.model_path)
        expected = list(getattr(self.model, 'feature_names_in_', []))
        if expected != FEATURES:
            raise ValueError('Model feature schema mismatch; retrain with pipeline.py train.')
        self.feature_columns = expected
        self.metadata = load_metadata(self.metadata_path, self.model_path)
        if self.metadata['status'] == 'available' and self.metadata.get('feature_version') != VERSION:
            raise ValueError('Model feature version mismatch; regenerate training artifacts.')

    def recommend(self, group_prefs, top_n=10, filter_location=None, filter_cuisine=None,
                  max_budget=None, min_rating=None, require_booking=None, require_online=None):
        if isinstance(top_n, bool) or not isinstance(top_n, int) or not 1 <= top_n <= 50:
            raise ValueError('top_n must be an integer from 1 to 50.')
        for value, low, high, label in [(max_budget, 0, float('inf'), 'Maximum budget'),
                                       (min_rating, 0, 5, 'Minimum rating')]:
            if value is not None and (not np.isfinite(value) or value < low or value > high
                                      or label == 'Maximum budget' and value == 0):
                raise ValueError(label + ' is outside the valid range.')
        profile = group_prefs.compute_group_profile()
        x = self.builder.build(group_prefs)[self.feature_columns]
        scores = np.asarray(self.model.predict(x), dtype=float)
        if not np.isfinite(scores).all():
            raise ValueError('Model returned invalid scores.')
        mask = np.ones(len(self.df), dtype=bool)
        if filter_location:
            mask &= np.array([normalize_text(filter_location) == l for l in self.locations_list])
        if filter_cuisine:
            mask &= np.array([normalize_text(filter_cuisine) in c for c in self.builder.cuisines])
        if max_budget is not None:
            mask &= self.df.cost_for_two.le(max_budget).to_numpy()
        # Member minimum ratings are an explicit requirement (75th percentile profile).
        rating_floor = max(profile['min_rating'], min_rating if min_rating is not None else 0)
        if rating_floor > 0:
            mask &= self.df.rating.ge(rating_floor).to_numpy()
        if require_booking is True or profile['booking_required']:
            mask &= self.df.book_table.eq(1).to_numpy()
        if require_online is True:
            mask &= self.df.online_order.eq(1).to_numpy()
        valid = np.flatnonzero(mask)
        # Filter first, then retain the highest-scoring eligible branch per name.
        # Continue down the full ranking so duplicates do not consume Top-N slots.
        # Restaurant ID breaks ties independently of catalogue row order.
        ranked = sorted(valid, key=lambda i: (-scores[i], self._restaurant_ids[i]))
        ordered, seen_names = [], set()
        for idx in ranked:
            key = self._restaurant_name_keys[idx]
            if key in seen_names:
                continue
            seen_names.add(key)
            ordered.append(idx)
            if len(ordered) == top_n:
                break
        recs = []
        for rank, idx in enumerate(ordered, 1):
            row, f = self.df.iloc[idx], x.iloc[idx]
            reasons, cautions = [], []
            if any(m.preferred_cuisines for m in group_prefs.members) and f.cuisine_match > 0:
                reasons.append(f'Cuisine preference coverage {f.cuisine_match:.0%}')
            if pd.isna(row.cost_for_two):
                cautions.append('Cost is unknown')
            elif all(row.cost_for_two <= m.budget for m in group_prefs.members):
                reasons.append('Listed cost for two is within every member budget')
            else:
                cautions.append('Listed cost exceeds at least one member budget')
            if any(m.preferred_location for m in group_prefs.members) and f.location_match > 0:
                reasons.append(f'Neighborhood name match {f.location_match:.0%}; no distance measurement')
            if profile['has_vegetarian'] or profile['has_vegan']:
                cautions.append('Dietary compatibility is unverified; confirm menu and preparation directly')
            if pd.notna(row.rating) and row.rating >= 4:
                reasons.append(f'Listed rating {row.rating:.1f}/5')
            def number(key, integer=False):
                value = row[key]
                return None if pd.isna(value) else int(value) if integer else float(value)
            def flag(key):
                return None if pd.isna(row[key]) else bool(row[key] == 1)
            score = float(scores[idx])
            recs.append({'rank': rank, 'restaurant_id': str(row.restaurant_id),
                         'name': restaurant_display_name(row['name']) or str(row['name']),
                         **{k: str(row[k]) if pd.notna(row[k]) else 'Unknown'
                            for k in ['location', 'cuisines', 'rest_type']},
                         'cost_for_two': number('cost_for_two'), 'rating': number('rating'),
                         'votes': number('votes', True), 'online_order': flag('online_order'),
                         'book_table': flag('book_table'), 'compatibility_score': round(score, 4),
                         'suitability_score': round(score, 4),
                         'match_percentage': round(float(np.clip(score, 0, 1)) * 100, 1),
                         'score_interpretation': 'compatibility index, not probability',
                         'dietary_status': 'unverified' if profile['has_vegetarian'] or profile['has_vegan'] else 'not requested',
                         'breakdown': {k: round(float(f[k]) * 100, 1) for k in
                                       ['cuisine_match', 'budget_match', 'dietary_compatibility',
                                        'location_match', 'restaurant_type_match', 'group_agreement']},
                         'reasons': reasons, 'cautions': cautions,
                         'explanation': '; '.join(reasons + cautions) or 'Ranked by the benchmark compatibility model.'})
        message = ''
        if not recs:
            message = 'No restaurants match all active filters. Adjust filters explicitly.'
        elif len(recs) < top_n:
            message = f'Only {len(recs)} distinct restaurant names match all active filters.'
        return {'status': 'success', 'group_profile': profile,
                'group_summary': {**profile, 'locations': profile['preferred_locations'],
                                  'restaurant_types': profile['preferred_types'],
                                  'total_candidates_scored': len(valid)},
                'total_candidates_evaluated': len(valid), 'recommendations': recs,
                'filters_relaxed': False,
                'message': message,
                'ranking_policy': 'One result per restaurant name; highest-scoring matching branch shown.',
                'limitations': ['Dietary information is unverified.',
                               'Scores approximate a constructed target, not human satisfaction.',
                               'Time/day are collected context only; no opening hours or trained time/day effect.']}
