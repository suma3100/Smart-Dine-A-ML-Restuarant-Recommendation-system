"""Regressions for repeated branch names in a single recommendation list."""
import pandas as pd
import pytest
from SmartDine.src.group_preferences import GroupPreferences, MemberPreference
from SmartDine.src.recommendation import SmartDineRecommender


def reload_catalogue(engine, frame):
    frame.to_csv(engine.data_path, index=False)
    return SmartDineRecommender(engine.data_path, engine.model_path)


def italian_group():
    return GroupPreferences([MemberPreference(preferred_cuisines=['Italian'], budget=500, min_rating=0)])


def with_branch(restaurants, name='Bistro'):
    branch = restaurants.iloc[0].to_dict()
    branch.update(restaurant_id='z', name=name, location='South', cost_for_two=200)
    return pd.concat([restaurants, pd.DataFrame([branch])], ignore_index=True)


def test_duplicate_branches_do_not_consume_top_n_slots(engine, restaurants):
    engine = reload_catalogue(engine, with_branch(restaurants))
    result = engine.recommend(italian_group(), top_n=3)
    rows = result['recommendations']
    assert len(rows) == 3
    assert {row['name'] for row in rows} == {'Bistro', 'Budget', 'Unknown'}
    assert [row['rank'] for row in rows] == [1, 2, 3]
    assert 'One result per restaurant name' in result['ranking_policy']


def test_best_scoring_branch_is_kept(engine, restaurants):
    engine = reload_catalogue(engine, with_branch(restaurants))
    rows = engine.recommend(italian_group(), top_n=3)['recommendations']
    chosen = next(row for row in rows if row['name'] == 'Bistro')
    assert chosen['restaurant_id'] == 'z'
    assert chosen['cost_for_two'] == 200


def test_deduplication_happens_after_location_and_service_filters(engine, restaurants):
    engine = reload_catalogue(engine, with_branch(restaurants))
    result = engine.recommend(italian_group(), top_n=10, filter_location='North', require_booking=True)
    assert [row['restaurant_id'] for row in result['recommendations']] == ['b']
    assert result['recommendations'][0]['book_table'] is True
    assert result['filters_relaxed'] is False


@pytest.mark.parametrize('variant', [' BISTRO  ', 'Bistro!', 'Ｂｉｓｔｒｏ', 'bis-tro'])
def test_display_name_variants_do_not_repeat(engine, restaurants, variant):
    engine = reload_catalogue(engine, with_branch(restaurants, name=variant))
    rows = engine.recommend(italian_group(), top_n=10)['recommendations']
    assert len(rows) == 3
    assert not {'b', 'z'} <= {row['restaurant_id'] for row in rows}


def test_fewer_distinct_names_return_fewer_results_without_fallback(engine, restaurants):
    frame = with_branch(restaurants).query("restaurant_id in ['b', 'z']")
    engine = reload_catalogue(engine, frame)
    result = engine.recommend(italian_group(), top_n=10)
    assert len(result['recommendations']) == 1
    assert 'Only 1 distinct restaurant' in result['message']
    assert result['filters_relaxed'] is False


def test_tied_branch_selection_is_stable_across_row_order(engine, restaurants):
    frame = with_branch(restaurants)
    first = reload_catalogue(engine, frame)
    first.model.coef_[:] = 0
    expected = first.recommend(italian_group(), top_n=3)
    second = reload_catalogue(engine, frame.iloc[::-1])
    second.model.coef_[:] = 0
    assert [row['restaurant_id'] for row in expected['recommendations']] == ['a', 'b', 'c']
    assert second.recommend(italian_group(), top_n=3) == expected


def test_missing_names_do_not_merge_unrelated_restaurant_ids(engine, restaurants):
    frame = restaurants.copy()
    frame['name'] = [None, '', None]
    engine = reload_catalogue(engine, frame)
    rows = engine.recommend(italian_group(), top_n=10)['recommendations']
    assert {row['restaurant_id'] for row in rows} == {'a', 'b', 'c'}


@pytest.mark.parametrize('encoding_rounds', [1, 4, 6])
def test_corrupted_accented_branch_names_are_repaired_and_not_repeated(engine, restaurants, encoding_rounds):
    correct = 'Moto Store & Caf\u00e9'
    corrupted = correct
    for _ in range(encoding_rounds):
        corrupted = corrupted.encode('utf-8').decode('latin1')
    restaurants.loc[0, 'name'] = correct
    engine = reload_catalogue(engine, with_branch(restaurants, corrupted))
    rows = engine.recommend(italian_group(), top_n=10)['recommendations']
    assert len(rows) == 3
    assert sum(row['name'] == correct for row in rows) == 1
    assert all('\u00c3' not in row['name'] for row in rows)


def test_accented_and_plain_display_names_do_not_repeat(engine, restaurants):
    restaurants.loc[0, 'name'] = 'Caf\u00e9 Corner'
    engine = reload_catalogue(engine, with_branch(restaurants, 'Cafe Corner'))
    assert len(engine.recommend(italian_group(), top_n=10)['recommendations']) == 3
