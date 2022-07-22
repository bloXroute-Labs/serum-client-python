import asyncio
import json
from typing import TYPE_CHECKING, Type, Optional, AsyncGenerator

import aiohttp
from jsonrpc import JsonRpcRequest, JsonRpcResponse
from solana import keypair

from bxserum import transaction
from bxserum.provider import Provider, constants
from bxserum.provider.base import NotConnectedException
from bxserum.provider.wsrpc import ProtoJsonRpcResponse

if TYPE_CHECKING:
    # noinspection PyUnresolvedReferences,PyProtectedMember
    from grpclib._protocols import IProtoMessage

    # noinspection PyProtectedMember
    from betterproto import _MetadataLike, Deadline, T


class WsProvider(Provider):
    _ws: Optional[aiohttp.ClientWebSocketResponse] = None

    _endpoint: str
    _session: aiohttp.ClientSession
    _request_id: int
    _request_lock: asyncio.Lock
    _private_key: Optional[keypair.Keypair]

    # noinspection PyMissingConstructor
    def __init__(
        self,
        endpoint: str = constants.MAINNET_API_WS,
        private_key: Optional[str] = None,
    ):
        self._endpoint = endpoint
        self._session = aiohttp.ClientSession()
        self._request_id = 1
        self._request_lock = asyncio.Lock()

        if private_key is None:
            try:
                self._private_key = transaction.load_private_key_from_env()
            except EnvironmentError:
                self._private_key = None
        else:
            self._private_key = transaction.load_private_key(private_key)

    async def connect(self):
        if self._ws is None:
            self._ws = await self._session.ws_connect(self._endpoint)

    def private_key(self) -> Optional[keypair.Keypair]:
        return self._private_key

    async def close(self):
        ws = self._ws
        if ws is not None:
            await ws.close()

        session = self._session
        if session is not None:
            await session.close()

    async def _next_request_id(self) -> str:
        async with self._request_lock:
            previous = self._request_id
            self._request_id += 1
            return str(previous)

    async def _create_request(
        self, route: str, request: "IProtoMessage"
    ) -> JsonRpcRequest:
        return JsonRpcRequest(
            await self._next_request_id(), _ws_endpoint(route), request
        )

    async def _unary_unary(
        self,
        route: str,
        request: "IProtoMessage",
        response_type: Type["T"],
        *,
        timeout: Optional[float] = None,
        deadline: Optional["Deadline"] = None,
        metadata: Optional["_MetadataLike"] = None,
    ) -> "T":
        ws = self._ws
        if ws is None:
            raise NotConnectedException()

        request = await self._create_request(route, request)
        await ws.send_json(request.to_json())

        raw_result = await ws.receive_json()
        return ProtoJsonRpcResponse(response_type).from_json(raw_result)

    async def _unary_stream(
        self,
        route: str,
        request: "IProtoMessage",
        response_type: Type["T"],
        *,
        timeout: Optional[float] = None,
        deadline: Optional["Deadline"] = None,
        metadata: Optional["_MetadataLike"] = None,
    ) -> AsyncGenerator["T", None]:
        ws = self._ws
        if ws is None:
            raise NotConnectedException()

        request = await self._create_request(route, request)
        await ws.send_json(request.to_json())

        # https://bloxroute.atlassian.net/browse/BX-4123 this doesn't really work since it'll intercept all kinds of message
        msg: aiohttp.WSMessage
        async for msg in ws:
            rpc_result = JsonRpcResponse.from_json(json.loads(msg.data))
            yield _deserialize_result(rpc_result, response_type)


def _ws_endpoint(route: str) -> str:
    return route.split("/")[-1]


def _deserialize_result(rpc_response: JsonRpcResponse, response_type: Type["T"]) -> "T":
    if rpc_response.error is None:
        return response_type().from_dict(rpc_response.result)

    raise rpc_response.error


def ws() -> Provider:
    return WsProvider()


def ws_testnet() -> Provider:
    return WsProvider(constants.TESTNET_API_WS)


def ws_local() -> Provider:
    return WsProvider(constants.LOCAL_API_WS)
