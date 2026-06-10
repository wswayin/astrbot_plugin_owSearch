import tempfile
import unittest
from pathlib import Path

from owsearch.cache.identity_store import IdentityStore
from owsearch.models import PlayerIdentity


class IdentityStoreTests(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = IdentityStore(Path(temp_dir) / "identities.json")
            identity = PlayerIdentity(
                query="Player#12345",
                full_id="Player#12345",
                bnet_id="12345",
                customer_token="token-value",
            )
            store.put(identity)
            loaded = store.get("player#12345")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.customer_token, "token-value")


if __name__ == "__main__":
    unittest.main()
