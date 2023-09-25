from http import HTTPStatus

import httpretty

import settings

from .setup_data import CONFIG_JSON_STONEGATE_BODY, MERCHANT_URL, SECRET_ACTEOL_JOIN


def assert_correct_happy_path_calls(test, mock_find_user, mock_patch_ctc_id, mock_put_hermes_credentials):
    assert mock_find_user.call_count == 1
    assert mock_patch_ctc_id.call_count == 1
    assert mock_put_hermes_credentials.call_count == 1

    assert mock_find_user.request_json["SearchFilters"]["MemberNumber"] == test.card_number
    assert mock_patch_ctc_id.request_json["CtcID"] == test.ctc_id
    assert mock_put_hermes_credentials.request_json["card_number"] == test.card_number
    assert mock_put_hermes_credentials.request_json["merchant_identifier"] == test.ctc_id


class TestStoneGateAdd:
    @httpretty.activate
    def test_happy_path(
        self,
        test_vars,
        patch_balance_login,
        client,
        http_pretty_mock,
        mock_stonegate_signals,
    ):
        test = test_vars()

        patch_balance_login({"card_number": test.card_number}, SECRET_ACTEOL_JOIN, CONFIG_JSON_STONEGATE_BODY)

        mock_find_user = http_pretty_mock(
            f"{MERCHANT_URL}/api/Customer/FindCustomerDetails",
            httpretty.POST,
            HTTPStatus.OK,
            test.customer_details_response,
        )
        mock_patch_ctc_id = http_pretty_mock(f"{MERCHANT_URL}/api/Customer/Patch", httpretty.PATCH, HTTPStatus.OK, {})

        mock_put_hermes_credentials = http_pretty_mock(
            f"{settings.HERMES_URL}/schemes/accounts/{test.account_id}/credentials", httpretty.PUT, HTTPStatus.OK, {}
        )

        # test Set up done - now Make call to balance api end point
        balance_response = client.get(
            f"/stonegate/balance?scheme_account_id={test.account_id}"
            f"&user_id={test.user_id}&bink_user_id={test.bink_user_id}"
            f"&journey_type=2"
            "&credentials=xxx&token=xxx"
        )

        assert balance_response.status_code == 200
        assert balance_response.json == {
            "points": int(test.points_balance),
            "points_label": str(int(test.points_balance)),
            "value": 0.0,
            "value_label": "",
            "scheme_account_id": test.account_id,
            "user_set": test.user_id,
            "bink_user_id": test.bink_user_id,
            "reward_tier": 0,
            "vouchers": [],
        }

        assert mock_stonegate_signals.name_list == [
            "send-audit-request",
            "send-audit-response",
            "record-http-request",
            "record-http-request",
            "log-in-success",
        ]

        assert_correct_happy_path_calls(test, mock_find_user, mock_patch_ctc_id, mock_put_hermes_credentials)

    @httpretty.activate
    def test_invalid_card_number(
        self,
        test_vars,
        patch_balance_login,
        client,
        http_pretty_mock,
        mock_stonegate_signals,
    ):
        test = test_vars()

        patch_balance_login({"card_number": test.card_number}, SECRET_ACTEOL_JOIN, CONFIG_JSON_STONEGATE_BODY)

        mock_find_user = http_pretty_mock(
            f"{MERCHANT_URL}/api/Customer/FindCustomerDetails",
            httpretty.POST,
            HTTPStatus.OK,
            test.customer_details_not_found_response,
        )
        mock_patch_ctc_id = http_pretty_mock(f"{MERCHANT_URL}/api/Customer/Patch", httpretty.PATCH, HTTPStatus.OK, {})

        mock_put_hermes_credentials = http_pretty_mock(
            f"{settings.HERMES_URL}/schemes/accounts/{test.account_id}/credentials", httpretty.PUT, HTTPStatus.OK, {}
        )

        # test Set up done - now Make call to balance api end point
        balance_response = client.get(
            f"/stonegate/balance?scheme_account_id={test.account_id}"
            f"&user_id={test.user_id}&bink_user_id={test.bink_user_id}"
            f"&journey_type=2"
            "&credentials=xxx&token=xxx"
        )

        assert balance_response.status_code == 403
        assert mock_find_user.call_count == 1
        assert mock_patch_ctc_id.call_count == 0
        assert mock_put_hermes_credentials.call_count == 0

        assert mock_stonegate_signals.name_list == [
            "send-audit-request",
            "send-audit-response",
            "record-http-request",
            "request-fail",
            "log-in-fail",
        ]
