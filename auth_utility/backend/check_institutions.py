import os
import plaid
from plaid.api import plaid_api
from plaid.model.institutions_search_request import InstitutionsSearchRequest
from plaid.model.country_code import CountryCode
from plaid.model.products import Products
from dotenv import load_dotenv, find_dotenv

# Load .env
load_dotenv(find_dotenv())

PLAID_CLIENT_ID = os.getenv("PLAID_CLIENT_ID")
PLAID_SECRET = os.getenv("PLAID_SECRET")
PLAID_ENV = os.getenv("PLAID_ENV", "sandbox")

host = getattr(plaid.Environment, PLAID_ENV.capitalize())

configuration = plaid.Configuration(
    host=host,
    api_key={
        "clientId": PLAID_CLIENT_ID,
        "secret": PLAID_SECRET,
    },
)

api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)


def check_institution(name):
    print(f"Checking {name}...")
    try:
        request = InstitutionsSearchRequest(
            query=name,
            products=[
                Products("transactions")
            ],  # Just to filter, though we want to see ALL supported
            country_codes=[CountryCode("US")],
        )
        response = client.institutions_search(request)
        if response.institutions:
            inst = response.institutions[0]
            print(f"Found: {inst.name} ({inst.institution_id})")
            print(f"Supported Products: {inst.products}")
        else:
            print(f"No institution found for '{name}'")
    except plaid.ApiException as e:
        print(f"Error checking {name}: {e}")


if __name__ == "__main__":
    check_institution("E-TRADE")
    check_institution("Marcus")
