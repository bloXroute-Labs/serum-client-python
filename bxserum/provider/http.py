import datetime
from typing import Type, AsyncGenerator, Optional, TYPE_CHECKING, List

import aiohttp
from solana import keypair

from bxserum import proto, transaction
from bxserum.provider import constants
from bxserum.provider.base import Provider
from bxserum.provider.http_error import map_response

if TYPE_CHECKING:
    # noinspection PyUnresolvedReferences,PyProtectedMember
    from grpclib._protocols import IProtoMessage

    # noinspection PyProtectedMember
    from betterproto import _MetadataLike, Deadline, T


class HttpProvider(Provider):
    _endpoint: str
    _session: aiohttp.ClientSession
    _private_key: Optional[keypair.Keypair]

    # noinspection PyMissingConstructor
    def __init__(
        self,
        endpoint: str = constants.MAINNET_API_HTTP,
        private_key: Optional[str] = None,
    ):
        self._endpoint = f"{endpoint}/api/v1"
        self._session = aiohttp.ClientSession()

        if private_key is None:
            try:
                self._private_key = transaction.load_private_key_from_env()
            except EnvironmentError:
                self._private_key = None
        else:
            self._private_key = transaction.load_private_key(private_key)

    async def connect(self):
        pass

    def private_key(self) -> Optional[keypair.Keypair]:
        return self._private_key

    async def close(self):
        await self._session.close()

    async def get_markets(self) -> proto.GetMarketsResponse:
        async with self._session.get(f"{self._endpoint}/market/markets") as res:
            return await map_response(res, proto.GetMarketsResponse())

    async def get_orderbook(
        self, *, market: str = "", limit: int = 0
    ) -> proto.GetOrderbookResponse:
        async with self._session.get(
            f"{self._endpoint}/market/orderbooks/{market}?limit={limit}"
        ) as res:
            return await map_response(res, proto.GetOrderbookResponse())

    async def get_tickers(self, *, market: str = "") -> proto.GetTickersResponse:
        async with self._session.get(
            f"{self._endpoint}/market/tickers/{market}"
        ) as res:
            return await map_response(res, proto.GetTickersResponse())

    async def get_orders(
        self,
        *,
        market: str = "",
        status: proto.OrderStatus = 0,
        side: proto.Side = 0,
        types: List[proto.OrderType] = [],
        from_: Optional[datetime.datetime] = None,
        limit: int = 0,
        direction: proto.Direction = 0,
        address: str = "",
    ) -> proto.GetOrdersResponse:
        raise NotImplementedError()

    async def get_open_orders(
        self,
        *,
        market: str = "",
        side: proto.Side = 0,
        types: List[proto.OrderType] = [],
        from_: Optional[datetime.datetime] = None,
        limit: int = 0,
        direction: proto.Direction = proto.Direction.D_ASCENDING,
        address: str = "",
    ) -> proto.GetOpenOrdersResponse:
        async with self._session.get(
            f"{self._endpoint}/trade/orders/{market}"
            f"?address={address}"
            f"&side={side}"
            f"&types=OT_LIMIT"
            f"&direction={direction.name}"
        ) as res:
            return await map_response(res, proto.GetOpenOrdersResponse())

    async def get_order_by_i_d(
        self, *, order_i_d: str = ""
    ) -> proto.GetOrderByIDResponse:
        # TODO
        raise NotImplementedError()

    async def get_unsettled(
        self, *, market: str = "", owner: str = ""
    ) -> proto.GetUnsettledResponse:
        async with self._session.get(
            f"{self._endpoint}/trade/unsettled/{market}" f"?owner={owner}"
        ) as res:
            return await map_response(res, proto.GetUnsettledResponse())

    async def get_account_balance(
            self, owner_address: str = ""
    ) -> proto.GetAccountBalanceResponse:
        async with self._session.get(
            f"{self._endpoint}/account/balance?ownerAddress={owner_address}"
        ) as res:
            return await map_response(res, proto.GetAccountBalanceResponse())

    async def post_order(
        self,
        *,
        owner_address: str = "",
        payer_address: str = "",
        market: str = "",
        side: "proto.Side" = 0,
        type: List["proto.OrderType"] = [],
        amount: float = 0,
        price: float = 0,
        open_orders_address: str = "",
        client_order_i_d: int = 0,
    ) -> proto.PostOrderResponse:
        request = proto.PostOrderRequest(
            owner_address,
            payer_address,
            market,
            side,
            type,
            amount,
            price,
            open_orders_address,
            client_order_i_d,
        )

        async with self._session.post(
            f"{self._endpoint}/trade/place", json=request.to_dict()
        ) as res:
            return await map_response(res, proto.PostOrderResponse())

    async def post_cancel_order(
        self,
        *,
        order_i_d: str = "",
        side: "proto.Side" = 0,
        market_address: str = "",
        owner_address: str = "",
        open_orders_address: str = "",
    ) -> proto.PostCancelOrderResponse:
        request = proto.PostCancelOrderRequest(
            order_i_d, side, market_address, owner_address, open_orders_address,
        )

        async with self._session.post(
            f"{self._endpoint}/trade/cancel", json=request.to_dict()
        ) as res:
            return await map_response(res, proto.PostCancelOrderResponse())

    async def post_cancel_by_client_order_i_d(
        self,
        *,
        client_order_i_d: int = 0,
        market_address: str = "",
        owner_address: str = "",
        open_orders_address: str = "",
    ) -> proto.PostCancelOrderResponse:
        request = proto.PostCancelByClientOrderIDRequest(
            client_order_i_d, market_address, owner_address, open_orders_address,
        )

        async with self._session.post(
            f"{self._endpoint}/trade/cancelbyid", json=request.to_dict()
        ) as res:
            return await map_response(res, proto.PostCancelOrderResponse())

    async def post_cancel_all(
        self,
        *,
        market: str = "",
        owner_address: str = "",
        open_orders_addresses: List[str] = "",
    ) -> proto.PostCancelAllResponse:
        request = proto.PostCancelAllRequest(
            market, owner_address, open_orders_addresses
        )
        async with self._session.post(
            f"{self._endpoint}/trade/cancelall", json=request.to_dict()
        ) as res:
            return await map_response(res, proto.PostCancelAllResponse())

    async def post_settle(
        self,
        *,
        owner_address: str = "",
        market: str = "",
        base_token_wallet: str = "",
        quote_token_wallet: str = "",
        open_orders_address: str = "",
    ) -> proto.PostSettleResponse:
        request = proto.PostSettleRequest(
            owner_address, market, base_token_wallet, quote_token_wallet, open_orders_address,
        )
        async with self._session.post(
            f"{self._endpoint}/trade/settle", json=request.to_dict()
        ) as res:
            return await map_response(res, proto.PostSettleResponse())

    async def post_submit(
        self, *, transaction: str = "", skip_pre_flight: bool = False
    ) -> proto.PostSubmitResponse:
        request = proto.PostSubmitRequest(transaction, skip_pre_flight)
        async with self._session.post(
            f"{self._endpoint}/trade/submit", json=request.to_dict()
        ) as res:
            return await map_response(res, proto.PostSubmitResponse())

    async def post_replace_by_client_order_i_d(
        self,
        *,
        owner_address: str = "",
        payer_address: str = "",
        market: str = "",
        side: "proto.Side" = 0,
        type: List["proto.OrderType"] = [],
        amount: float = 0,
        price: float = 0,
        open_orders_address: str = "",
        client_order_i_d: int = 0,
    ) -> proto.PostOrderResponse:
        request = proto.PostOrderRequest(
            owner_address,
            payer_address,
            market,
            side,
            type,
            amount,
            price,
            open_orders_address,
            client_order_i_d,
        )

        async with self._session.post(
            f"{self._endpoint}/trade/replacebyclientid", json=request.to_dict()
        ) as res:
            return await map_response(res, proto.PostOrderResponse())

    async def post_replace_order(
        self,
        *,
        owner_address: str = "",
        payer_address: str = "",
        market: str = "",
        side: "proto.Side" = 0,
        type: List["proto.OrderType"] = [],
        amount: float = 0,
        price: float = 0,
        open_orders_address: str = "",
        client_order_i_d: int = 0,
        order_id: str
    ) -> proto.PostOrderResponse:
        request = proto.PostReplaceOrderRequest(
            owner_address,
            payer_address,
            market,
            side,
            type,
            amount,
            price,
            open_orders_address,
            client_order_i_d,
            order_id
        )

        async with self._session.post(
            f"{self._endpoint}/trade/replace", json=request.to_dict()
        ) as res:
            return await map_response(res, proto.PostOrderResponse())


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
        # seems to require yield some result otherwise this isn't an async generator?
        yield NotImplementedError("streams not supported for HTTP")
        raise NotImplementedError("streams not supported for HTTP")


def http() -> Provider:
    return HttpProvider()


def http_testnet() -> Provider:
    return HttpProvider(constants.TESTNET_API_HTTP)


def http_local() -> Provider:
    return HttpProvider(constants.LOCAL_API_HTTP)
