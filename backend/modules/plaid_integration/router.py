from fastapi import APIRouter, HTTPException
import time
import plaid
from plaid.api import plaid_api
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from pydantic import BaseModel
from backend.core.config import settings

router = APIRouter(prefix="/plaid", tags=["Plaid"])

# Setup Plaid Client
host = getattr(plaid.Environment, settings.PLAID_ENV.capitalize())
configuration = plaid.Configuration(
    host=host,
    api_key={
        "clientId": settings.PLAID_CLIENT_ID,
        "secret": settings.PLAID_SECRET,
    },
)

api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)

class TokenExchangeRequest(BaseModel):
    public_token: str

@router.post("/create_link_token")
async def create_link_token() -> dict:
    try:
        # For our local app, we usually use these core products
        products = [Products("transactions"), Products("investments"), Products("liabilities")]
        country_codes = [CountryCode("US")]

        request_args = {
            "products": products,
            "country_codes": country_codes,
            "language": "en",
            "client_name": "Plaid Local App",
            "user": LinkTokenCreateRequestUser(client_user_id=str(time.time())),
        }

        request = LinkTokenCreateRequest(**request_args)
        response = client.link_token_create(request)
        return response.to_dict()
    except plaid.ApiException as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/set_access_token")
async def set_access_token(request: TokenExchangeRequest) -> dict:
    try:
        exchange_request = ItemPublicTokenExchangeRequest(
            public_token=request.public_token
        )
        exchange_response = client.item_public_token_exchange(exchange_request)
        access_token = exchange_response["access_token"]
        
        # Here we return the access token. Later, we can save it to the DB if we want.
        # For now, we mimic the old behavior and let the user put it in .env
        return {"access_token": access_token}
    except plaid.ApiException as e:
        raise HTTPException(status_code=500, detail=str(e))
