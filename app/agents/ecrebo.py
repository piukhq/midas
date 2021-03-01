import time
import typing as t
from decimal import Decimal
from uuid import uuid4

import arrow
import requests
from app import constants
from app.agents.base import ApiMiner
from app.agents.exceptions import ACCOUNT_ALREADY_EXISTS, STATUS_LOGIN_FAILED, LoginError, RegistrationError
from app.audit import AuditLogger
from app.configuration import Configuration
from app.encryption import hash_ids
from app.tasks.resend_consents import ConsentStatus
from app.vouchers import VoucherState, VoucherType, get_voucher_state, voucher_state_names

from blinker import signal


class Ecrebo(ApiMiner):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        config = Configuration(scheme_slug, Configuration.JOIN_HANDLER)
        self.base_url = config.merchant_url
        self.auth = config.security_credentials["outbound"]["credentials"][0]["value"]
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)

        # Empty iterable for journeys to turn audit logging off by default. Add journeys per merchant to turn on.
        self.audit_logger = AuditLogger(channel=self.channel, journeys=())

    def _authenticate(self):
        """
        Returns an Ecrebo API auth token to use in subsequent requests.
        """
        login_path = "/v1/auth/login"
        resp = requests.post(
            f"{self.base_url}{login_path}", json={"name": self.auth["username"], "password": self.auth["password"]}
        )
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:  # Try to capture as much as possible for metrics
            try:
                latency_seconds = e.response.elapsed.total_seconds()
            except AttributeError:
                latency_seconds = 0
            signal("record-http-request").send(self, slug=self.scheme_slug, endpoint=login_path,
                                               latency=latency_seconds, response_code=e.response.status_code)
            raise
        else:
            signal("record-http-request").send(self, slug=self.scheme_slug, endpoint=resp.request.path_url,
                                               latency=resp.elapsed.total_seconds(), response_code=resp.status_code)

        return resp.json()["token"]

    def _make_headers(self, token):
        return {"Token": token, "Audit-Tag": str(uuid4())}

    def _get_card_number_and_uid(self, message):
        card_number, uid, *_ = message.split(":")
        return card_number, uid

    def _get_membership_response(self, endpoint: str) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        headers = self._make_headers(self._authenticate())

        # TODO: this retry loop can be removed when Ecrebo finish making their API synchronous.
        attempts = 5
        while attempts > 0:
            attempts -= 1

            resp = requests.get(url, headers=headers)
            try:
                resp.raise_for_status()
                signal("record-http-request").send(self, slug=self.scheme_slug, endpoint=resp.request.path_url,
                                                   latency=resp.elapsed.total_seconds(),
                                                   response_code=resp.status_code)
                return resp
            except requests.HTTPError as ex:  # Try to capture as much as possible for metrics
                try:
                    latency_seconds = ex.response.elapsed.total_seconds()
                except AttributeError:
                    latency_seconds = 0
                signal("record-http-request").send(self, slug=self.scheme_slug, endpoint=endpoint,
                                                   latency=latency_seconds, response_code=ex.response.status_code)
                if ex.response.status_code == 404:
                    raise LoginError(STATUS_LOGIN_FAILED)
                else:
                    raise  # base agent will convert this to an unknown error
            except (requests.RequestException, KeyError):
                # non-http errors will be retried a few times
                if attempts == 0:
                    raise
                else:
                    time.sleep(3)
            else:
                break

    def register(self, credentials):
        consents = credentials.get("consents", [])
        message_uid = str(uuid4())
        record_uid = hash_ids.encode(self.scheme_id)
        integration_service = Configuration.INTEGRATION_CHOICES[Configuration.SYNC_INTEGRATION][1].upper()

        consents_data = {c["slug"]: c["value"] for c in consents}
        data = {"data": self._get_registration_credentials(credentials, consents_data)}

        self.audit_logger.add_request(
            payload=data,
            scheme_slug=self.scheme_slug,
            handler_type=Configuration.JOIN_HANDLER,
            integration_service=integration_service,
            message_uid=message_uid,
            record_uid=record_uid,
        )

        resp = requests.post(
            f"{self.base_url}/v1/list/append_item/{self.RETAILER_ID}/assets/membership",
            json=data,
            headers=self._make_headers(self._authenticate()),
        )

        signal("record-http-request").send(self, slug=self.scheme_slug, endpoint=resp.request.path_url,
                                           latency=resp.elapsed.total_seconds(),
                                           response_code=resp.status_code)

        self.audit_logger.add_response(
            response=resp,
            scheme_slug=self.scheme_slug,
            handler_type=Configuration.JOIN_HANDLER,
            integration_service=integration_service,
            status_code=resp.status_code,
            message_uid=message_uid,
            record_uid=record_uid,
        )
        self.audit_logger.send_to_atlas()

        if resp.status_code == 409:
            signal("register-fail").send(self, slug=self.scheme_slug, channel=self.user_info["channel"])
            raise RegistrationError(ACCOUNT_ALREADY_EXISTS)
        else:
            try:
                resp.raise_for_status()
            except requests.HTTPError:
                signal("register-fail").send(self, slug=self.scheme_slug, channel=self.user_info["channel"])
                raise
            else:
                signal("register-success").send(self, slug=self.scheme_slug, channel=self.user_info["channel"])
                json = resp.json()
                message = json["publisher"][0]["message"]

        card_number, uid = self._get_card_number_and_uid(message)

        self.identifier = {"card_number": card_number, "merchant_identifier": uid}
        self.user_info["credentials"].update(self.identifier)

        if consents:
            self.consent_confirmation(consents, ConsentStatus.SUCCESS)

    def login(self, credentials):
        self.credentials = credentials
        consents = credentials.get("consents", [])
        message_uid = str(uuid4())
        record_uid = hash_ids.encode(self.scheme_id)
        integration_service = Configuration.INTEGRATION_CHOICES[Configuration.SYNC_INTEGRATION][1].upper()

        consents_data = {c["slug"]: c["value"] for c in consents}
        data = {"data": self._get_registration_credentials(credentials, consents_data)}

        self.audit_logger.add_request(
            payload=data,
            scheme_slug=self.scheme_slug,
            handler_type=Configuration.JOIN_HANDLER,
            integration_service=integration_service,
            message_uid=message_uid,
            record_uid=record_uid,
        )

        if "merchant_identifier" not in credentials:
            endpoint = f"/v1/list/query_item/{self.RETAILER_ID}/assets/membership/token/{credentials['card_number']}"
            try:
                resp = self._get_membership_response(endpoint)
                membership_data = resp.json()["data"]
                signal("log-in-success").send(self, slug=self.scheme_slug)

            except (KeyError, LoginError, requests.HTTPError, requests.RequestException):
                # Any of these exceptions mean the login has failed
                signal("log-in-fail").send(self, slug=self.scheme_slug)
                raise

            self.audit_logger.add_response(
                response=resp,
                scheme_slug=self.scheme_slug,
                handler_type=Configuration.JOIN_HANDLER,
                integration_service=integration_service,
                status_code=resp.status_code,
                message_uid=message_uid,
                record_uid=record_uid,
            )
            self.audit_logger.send_to_atlas()
            # TODO: do we actually need all three of these
            self.credentials["merchant_identifier"] = membership_data["uuid"]
            self.identifier = {"merchant_identifier": membership_data["uuid"]}
            self.user_info["credentials"].update(self.identifier)

    def _make_issued_voucher(self, voucher_type: VoucherType, json: dict, target_value: Decimal) -> dict:
        issue_date = arrow.get(json["issued"], "YYYY-MM-DD")
        expiry_date = arrow.get(json["expiry_date"], "YYYY-MM-DD")
        if "redeemed" in json:
            redeem_date = arrow.get(json["redeemed"], "YYYY-MM-DD")
        else:
            redeem_date = None

        state = get_voucher_state(
            issue_date=issue_date,
            redeem_date=redeem_date,
            expiry_date=expiry_date
        )

        voucher = {
            "state": voucher_state_names[state],
            "type": voucher_type.value,
            "issue_date": issue_date.timestamp,
            "expiry_date": expiry_date.timestamp,
            "code": json["code"],
            "value": target_value,
            "target_value": target_value,
        }

        if redeem_date:
            voucher["redeem_date"] = redeem_date.timestamp

        return voucher

    def _make_balance_response(
            self, voucher_type: VoucherType, value: Decimal, target_value: Decimal, issued_vouchers: t.List[dict]
    ) -> dict:
        return {
            "points": value,
            "value": value,
            "value_label": "",
            "vouchers": [
                {"state": voucher_state_names[VoucherState.IN_PROGRESS], "type": voucher_type.value, "value": value,
                 "target_value": target_value},
                *[self._make_issued_voucher(voucher_type, voucher, target_value) for voucher in issued_vouchers],
            ],
        }

    def _accumulator_balance(self, json: dict) -> dict:
        value = Decimal(json["config"]["pot_total"]) / 5
        target_value = Decimal(json["config"]["pot_goal"]) / 5
        issued_vouchers = json["vouchers"]
        return self._make_balance_response(VoucherType.ACCUMULATOR, value, target_value, issued_vouchers)

    def _stamps_balance(self, json: dict) -> dict:
        value = Decimal(json["config"]["stamps"])
        target_value = Decimal(json["config"]["stamps_goal"])
        issued_vouchers = json["vouchers"]
        return self._make_balance_response(VoucherType.STAMPS, value, target_value, issued_vouchers)

    def balance(self):
        endpoint = (
            f"/v1/list/query_item/{self.RETAILER_ID}/assets/membership/uuid/{self.credentials['merchant_identifier']}"
        )
        resp = self._get_membership_response(endpoint)
        rewards = resp.json()["data"]["membership_rewards"]

        # sometimes this data is in a sub-object called "rewards", so use that if it's present.
        if "rewards" in rewards:
            rewards = rewards["rewards"]

        # if we got this far without crashing, and the journey type is "link"...
        # then we are doing the first valid balance update since the join first occurred.
        # in this case, we must tell hermes to set the join date, not the link date.
        # if we just set the create journey to "join", hermes will set the card to pending,
        # and then attempt to get a balance update. i added the "join-with-balance" identifier
        # to allow hermes to simply set the join date, and stop there.
        if self.user_info.get("from_register") is True:
            self.create_journey = "join-with-balance"

        campaign_type = rewards["type"].strip()

        if campaign_type == "thresholdmarketing":
            return self._accumulator_balance(rewards)
        elif campaign_type == "punchcard":
            return self._stamps_balance(rewards)
        else:
            raise ValueError(f"Unsupported Ecrebo campaign type: {campaign_type}")

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []


class FatFace(Ecrebo):
    RETAILER_ID = "94"

    def __init__(self, retry_count, user_info, scheme_slug=None):
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)
        self.audit_logger.journeys = (Configuration.JOIN_HANDLER,)

    def _get_registration_credentials(self, credentials: dict, consents: dict) -> dict:
        return {
            "email": credentials[constants.EMAIL],
            "first_name": credentials[constants.FIRST_NAME],
            "surname": credentials[constants.LAST_NAME],
            "join_date": arrow.utcnow().format("YYYY-MM-DD"),
            "email_marketing": consents["email_marketing"],
            "source": "channel",
            "validated": True,
        }


class BurgerKing(Ecrebo):
    RETAILER_ID = "95"

    def _get_registration_credentials(self, credentials: dict, consents: dict) -> dict:
        return {
            "email": credentials[constants.EMAIL],
            "first_name": credentials[constants.FIRST_NAME],
            "last_name": credentials[constants.LAST_NAME],
            "postcode": credentials[constants.POSTCODE],
            "phone": credentials[constants.PHONE],
            "validated": True,
        }


class WhSmith(Ecrebo):
    RETAILER_ID = "100"

    def _get_registration_credentials(self, credentials: dict, consents: dict) -> dict:
        data = {
            "email": credentials[constants.EMAIL],
            "title": credentials[constants.TITLE],
            "first_name": credentials[constants.FIRST_NAME],
            "surname": credentials[constants.LAST_NAME],
            "mobile_number": credentials[constants.PHONE],
            "address_line1": credentials['address_1'],
            "city": credentials['town_city'],
            "postcode": credentials[constants.POSTCODE],
            "validated": True,
        }
        if credentials[constants.TITLE].lower() == "prefer not to say":
            del data['title']
        return data
