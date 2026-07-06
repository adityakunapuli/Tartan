"""Live End-to-End System Tests (Requires Valid Credentials)."""

import os
import pytest
import plaid
from plaid.api import plaid_api
from dotenv import load_dotenv, find_dotenv

from core.config import settings as Config

# Load env to check if we can run this
load_dotenv(find_dotenv())


@pytest.mark.skipif(
    not os.getenv("PLAID_CLIENT_ID") or not os.getenv("PLAID_SECRET"),
    reason="Missing Plaid credentials in .env",
)
def test_plaid_connectivity_live():
    """Verifies that the application can authenticate with Plaid Production/Sandbox."""
    # Setup Client directly (bypass Config class to be explicit)
    client_id = os.getenv("PLAID_CLIENT_ID")
    secret = os.getenv("PLAID_SECRET")
    env = os.getenv("PLAID_ENV", "sandbox")

    host = getattr(plaid.Environment, env.capitalize())
    configuration = plaid.Configuration(
        host=host,
        api_key={
            "clientId": client_id,
            "secret": secret,
        },
    )
    api_client = plaid.ApiClient(configuration)
    client = plaid_api.PlaidApi(api_client)

    # Make a simple call that doesn't require an access token

    from plaid.model.link_token_create_request import LinkTokenCreateRequest
    from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
    from plaid.model.products import Products
    from plaid.model.country_code import CountryCode

    try:
        request = LinkTokenCreateRequest(
            products=[Products("transactions")],
            client_name="Plaid Local Test",
            country_codes=[CountryCode("US")],
            language="en",
            user=LinkTokenCreateRequestUser(client_user_id="test_user_id"),
        )
        response = client.link_token_create(request)

        assert response["link_token"] is not None
        print(
            f"\n[LIVE] Successfully generated Link Token: {response['link_token'][:10]}..."
        )

    except plaid.ApiException as e:
        pytest.fail(f"Live Plaid connection failed: {e}")


@pytest.mark.skipif(
    not os.getenv("PLAID_ACCESS_TOKEN"),
    reason="No PLAID_ACCESS_TOKEN in .env for live sync test",
)
def test_live_sync_dry_run():
    """Attempts a 'dry run' sync with the first configured access token.

    This verifies that the Access Token is valid and the Item is not in an error state.
    """
    token = os.getenv("PLAID_ACCESS_TOKEN").split(",")[0].strip()

    # Setup Client
    client_id = os.getenv("PLAID_CLIENT_ID")
    secret = os.getenv("PLAID_SECRET")
    env = os.getenv("PLAID_ENV", "sandbox")
    host = getattr(plaid.Environment, env.capitalize())
    configuration = plaid.Configuration(
        host=host,
        api_key={"clientId": client_id, "secret": secret},
    )
    client = plaid_api.PlaidApi(plaid.ApiClient(configuration))

    from plaid.model.accounts_get_request import AccountsGetRequest

    try:
        request = AccountsGetRequest(access_token=token)
        response = client.accounts_get(request)

        assert len(response["accounts"]) > 0
        print(
            f"\n[LIVE] Successfully fetched {len(response['accounts'])} accounts for token."
        )

    except plaid.ApiException as e:
        pytest.fail(f"Live Sync (Dry Run) failed for token: {e}")
