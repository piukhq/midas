import json
from unittest.mock import patch

import httpretty
import pytest

import settings
from app.journeys.join import attempt_join, login_and_publish_status
from app.models import RetryTask
from app.scheme_account import JourneyTypes, SchemeAccountStatus, update_pending_join_account

settings.API_AUTH_ENABLED = False

retailers = ["itsu", "squaremeal", "wasabi"]
callback_retailers = ["bpl-viator"]


@httpretty.activate
@pytest.mark.parametrize("retailer_fixture", retailers, indirect=True)
@patch("app.journeys.join.login_and_publish_status", side_effect=login_and_publish_status)
@patch("app.journeys.join.update_pending_join_account", side_effect=update_pending_join_account)
def test_join(
    mock_login_and_publish_status,
    mock_update_pending_join_account,
    apply_login_patches,
    apply_hermes_patches,
    apply_mock_end_points,
    apply_db_patches,
    apply_wasabi_patches,
    retailer_fixture,
    redis_retry_pretty_fix,
):
    apply_login_patches()
    apply_db_patches()
    apply_mock_end_points()
    apply_wasabi_patches()
    apply_hermes_patches()
    user_info = {
        "user_set": "1",
        "bink_user_id": "1",
        "credentials": retailer_fixture["credentials"],
        "status": SchemeAccountStatus.JOIN_ASYNC_IN_PROGRESS,
        "journey_type": JourneyTypes.JOIN.value,
        "scheme_account_id": "123",
        "channel": "bink.com",
    }
    attempt_join(user_info["scheme_account_id"], "1", retailer_fixture["slug"], user_info)
    mock_login_and_publish_status.assert_called()
    mock_update_pending_join_account.assert_called()
    # publish.balance called
    # send balance to hades called
    # publish transaction
    # publish status


@httpretty.activate
@pytest.mark.parametrize("retailer_fixture", callback_retailers, indirect=True)
@patch("app.agents.bpl.get_task")
@patch("app.journeys.join.login_and_publish_status", side_effect=login_and_publish_status)
@patch("app.journeys.join.update_pending_join_account", side_effect=update_pending_join_account)
def test_join_with_callback(
    mock_get_task,
    mock_login_and_publish_status,
    mock_update_pending_join_account,
    apply_login_patches,
    apply_mock_end_points,
    apply_db_patches,
    retailer_fixture,
    client,
):
    apply_login_patches()
    apply_db_patches()
    apply_mock_end_points()
    mock_get_task.return_value = RetryTask(awaiting_callback=True)
    user_info = {
        "user_set": "1",
        "bink_user_id": "1",
        "credentials": retailer_fixture["credentials"],
        "status": SchemeAccountStatus.JOIN_ASYNC_IN_PROGRESS,
        "journey_type": JourneyTypes.JOIN.value,
        "scheme_account_id": "123",
        "channel": "bink.com",
    }
    attempt_join(user_info["scheme_account_id"], "1", retailer_fixture["slug"], user_info)

    mock_login_and_publish_status.assert_called()
    mock_update_pending_join_account.assert_called()
    callback_endpoint = retailer_fixture["callback"]["callback_endpoint"]
    callback_data = retailer_fixture["callback"]["callback_data"]
    client.post(
        callback_endpoint,
        data=json.dumps(callback_data),
        headers={"Content-type": "application/json"},
    )

    # publish.balance called
    # send balance to hades called
    # publish transaction
    # publish status


@httpretty.activate
@pytest.mark.parametrize("retailer_fixture", retailers + callback_retailers, indirect=True)
def test_login(apply_login_patches, apply_mock_end_points, apply_db_patches, retailer_fixture, client):
    retailer_fixture["credentials"]["card_number"] = "123"
    apply_login_patches()
    apply_db_patches()
    apply_mock_end_points()
    scheme_account_id = "123"
    bink_user_id = "1"
    user_id = "1"
    balance_response = client.get(
        f"/{retailer_fixture['slug']}/balance?scheme_account_id={scheme_account_id}"
        f"&user_id={user_id}&bink_user_id={bink_user_id}"
        f"&journey_type=2"
        "&credentials=xxx&token=xxx"
    )
    assert balance_response.status_code == 200
    assert balance_response.json == "{}"
