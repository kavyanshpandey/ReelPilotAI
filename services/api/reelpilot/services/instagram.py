from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx

from reelpilot.config import Settings


class InstagramAPIError(RuntimeError):
    pass


def authorization_url(settings: Settings, state: str) -> str:
    if not settings.instagram_app_id:
        raise InstagramAPIError("Instagram OAuth is not configured")
    return "https://www.instagram.com/oauth/authorize?" + urlencode({
        "client_id": settings.instagram_app_id,
        "redirect_uri": settings.instagram_redirect_uri,
        "response_type": "code",
        "scope": "instagram_business_basic,instagram_business_manage_comments,instagram_business_manage_messages",
        "state": state,
    })


async def exchange_code(settings: Settings, code: str) -> tuple[str, datetime | None]:
    if not settings.instagram_app_id or not settings.instagram_app_secret:
        raise InstagramAPIError("Instagram OAuth is not configured")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post("https://api.instagram.com/oauth/access_token", data={
            "client_id": settings.instagram_app_id,
            "client_secret": settings.instagram_app_secret,
            "grant_type": "authorization_code",
            "redirect_uri": settings.instagram_redirect_uri,
            "code": code,
        })
        if response.is_error:
            raise InstagramAPIError("Instagram authorization code exchange failed")
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise InstagramAPIError("Instagram did not return an access token")
        return token, datetime.now(UTC) + timedelta(days=60)


async def graph_get(settings: Settings, path: str, token: str, **params):
    url = f"https://graph.instagram.com/{settings.instagram_api_version}/{path.lstrip('/')}"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, params={**params, "access_token": token})
    if response.is_error:
        try:
            payload = response.json()
            error = payload.get("error", {})
            message = error.get("message") or payload.get("message")
        except ValueError:
            message = None
        detail = f" ({message})" if message else ""
        raise InstagramAPIError(f"Instagram Graph API request failed with HTTP {response.status_code}{detail}")
    return response.json()


async def graph_get_all(settings: Settings, path: str, token: str, **params) -> list[dict]:
    """Read all pages for a small Graph API collection."""
    payload = await graph_get(settings, path, token, **params)
    rows = list(payload.get("data", []))
    next_url = (payload.get("paging") or {}).get("next")
    page_count = 1

    async with httpx.AsyncClient(timeout=30) as client:
        while next_url and page_count < 10:
            response = await client.get(next_url)
            if response.is_error:
                try:
                    error_payload = response.json()
                    error = error_payload.get("error", {})
                    message = error.get("message") or error_payload.get("message")
                except ValueError:
                    message = None
                detail = f" ({message})" if message else ""
                raise InstagramAPIError(f"Instagram Graph API request failed with HTTP {response.status_code}{detail}")
            payload = response.json()
            rows.extend(payload.get("data", []))
            next_url = (payload.get("paging") or {}).get("next")
            page_count += 1
    return rows
