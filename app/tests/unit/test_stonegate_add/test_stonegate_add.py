from http import HTTPStatus

import httpretty


def assert_correct_happy_path_calls(test, mock_call_data):
    assert mock_call_data["mock_find_user"].call_count == 1
    assert mock_call_data["mock_put_hermes_credentials"].call_count == 1

    assert mock_call_data["mock_find_user"].request_json["SearchFilters"]["MemberNumber"] == test.card_number
    assert mock_call_data["mock_put_hermes_credentials"].request_json["card_number"] == test.card_number
    assert mock_call_data["mock_put_hermes_credentials"].request_json["merchant_identifier"] == test.card_number


class TestStoneGateAdd:
    @httpretty.activate
    def test_add_happy_path(
        self,
        test_vars,
        apply_login_patches,
        apply_mock_end_points,
        client,
        mock_stonegate_signals,
    ):
        test = test_vars()
        mock_call_data = apply_mock_end_points(test, test.customer_details_response, HTTPStatus.OK)
        apply_login_patches(test, {"card_number": test.card_number})

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

        assert_correct_happy_path_calls(test, mock_call_data)
        assert mock_call_data["mock_patch_ctc_id"].call_count == 1
        assert mock_call_data["mock_patch_ctc_id"].request_json["CtcID"] == test.ctc_id

    @httpretty.activate
    def test_view_happy_path(
        self,
        test_vars,
        apply_login_patches,
        apply_mock_end_points,
        client,
        mock_stonegate_signals,
    ):
        test = test_vars()
        mock_call_data = apply_mock_end_points(test, test.customer_details_response, HTTPStatus.OK)
        apply_login_patches(test, {"card_number": test.card_number, "merchant_identifier": test.card_number})

        # test Set up done - now Make call to balance api end point
        balance_response = client.get(
            f"/stonegate/balance?scheme_account_id={test.account_id}"
            f"&user_id={test.user_id}&bink_user_id={test.bink_user_id}"
            f"&journey_type=3"
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
            "record-http-request",
            "log-in-success",
        ]

        assert_correct_happy_path_calls(test, mock_call_data)
        assert mock_call_data["mock_patch_ctc_id"].call_count == 0

    @httpretty.activate
    def test_invalid_card_number(
        self,
        test_vars,
        apply_login_patches,
        apply_mock_end_points,
        client,
        mock_stonegate_signals,
    ):
        test = test_vars()
        mock_call_data = apply_mock_end_points(test, test.customer_details_not_found_response, HTTPStatus.OK)
        apply_login_patches(test, {"card_number": test.card_number})

        # test Set up done - now Make call to balance api end point
        balance_response = client.get(
            f"/stonegate/balance?scheme_account_id={test.account_id}"
            f"&user_id={test.user_id}&bink_user_id={test.bink_user_id}"
            f"&journey_type=2"
            "&credentials=xxx&token=xxx"
        )

        assert balance_response.status_code == 436
        assert mock_call_data["mock_find_user"].call_count == 1
        assert mock_call_data["mock_patch_ctc_id"].call_count == 0
        assert mock_call_data["mock_put_hermes_credentials"].call_count == 0

        assert mock_stonegate_signals.name_list == [
            "send-audit-request",
            "send-audit-response",
            "record-http-request",
            "request-fail",
            "log-in-fail",
        ]
