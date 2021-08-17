import unittest

from user_auth_token import UserTokenStore

from settings import REDIS_URL


class TestUserTokenStore(unittest.TestCase):
    user_token_store = UserTokenStore(REDIS_URL)

    def test_user_token_store_add_and_delete_token(self):
        test_scheme_acct_id = "test_1"
        test_token = "testtoken"
        self.user_token_store.set(test_scheme_acct_id, test_token)
        saved_token = self.user_token_store.get(test_scheme_acct_id)
        self.assertEqual(saved_token, test_token)

        self.user_token_store.delete(test_scheme_acct_id)
        with self.assertRaises(UserTokenStore.NoSuchToken):
            self.user_token_store.get(test_scheme_acct_id)

    def tearDown(self):
        try:
            self.user_token_store.delete(1)
        except UserTokenStore.NoSuchToken:
            pass
