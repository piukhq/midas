from http import HTTPStatus

import httpretty

from .setup_data import CONFIG_JSON_STONEGATE_BODY, SECRET_ACTEOL_JOIN


class TestStoneGateAdd:
    @httpretty.activate
    def test_happy_path(
        self,
        patch_balance_login,
        client,
        http_pretty_find_user,
        http_pretty_user_patch,
        http_pretty_send_credentials,
        mock_stonegate_signals,
    ):
        account_id = 95812687
        user_id = "289645"
        bink_user_id = 678934
        patch_balance_login({"card_number": "1234567890"}, SECRET_ACTEOL_JOIN, CONFIG_JSON_STONEGATE_BODY)

        http_pretty_find_user(HTTPStatus.OK, {"ResponseData": [{"CtcID": 98923}]})
        http_pretty_user_patch(HTTPStatus.OK, {})
        http_pretty_send_credentials(account_id, HTTPStatus.OK, {})

        response = client.get(
            f"/stonegate/balance?scheme_account_id={account_id}"
            f"&user_id={user_id}&bink_user_id={bink_user_id}"
            f"&journey_type=2"
            "&credentials=xxx&token=xxx"
        )
        resp = response.json
        assert response.status_code == 200
        assert resp["points"] == 0
        assert resp["scheme_account_id"] == account_id
        assert resp["user_set"] == user_id
        assert resp["bink_user_id"] == bink_user_id
        assert resp["value"] == 0
        assert resp["reward_tier"] == 0
        assert resp["vouchers"] == []
        assert mock_stonegate_signals.name_list == [
            "send-audit-request",
            "send-audit-response",
            "record-http-request",
            "record-http-request",
            "log-in-success",
        ]
        print(resp)
