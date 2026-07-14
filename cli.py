from __future__ import annotations

from decimal import Decimal

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

import questionary
from pydantic import ValidationError
from bot.client import BinanceAPIError, BinanceFuturesTestnetClient
from bot.logging_config import configure_logging
from bot.orders import OrderService, build_limit_order, build_market_order, build_stop_market_order
from bot.models import OrderRequest


app = typer.Typer(add_completion=False, help="Place Binance Futures Testnet orders from the command line.")
console = Console()


@app.command()
def place(
    symbol: str = typer.Option(..., "--symbol", "-s", help="Trading symbol, for example BTCUSDT."),
    side: str = typer.Option(..., "--side", "-d", help="BUY or SELL."),
    order_type: str = typer.Option(..., "--type", "-t", help="MARKET or LIMIT."),
    quantity: str = typer.Option(..., "--quantity", "-q", help="Order quantity as a positive number."),
    price: str | None = typer.Option(None, "--price", "-p", help="Limit price, required only for LIMIT orders."),
    stop_price: str | None = typer.Option(None, "--stop-price", help="Stop price, required for STOP_MARKET orders."),
    time_in_force: str = typer.Option("GTC", "--time-in-force", help="Time in force for LIMIT orders."),
    client_order_id: str | None = typer.Option(None, "--client-order-id", help="Optional custom client order id."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate and print the payload without sending it."),
) -> None:
    """Submit a single futures order to Binance testnet."""

    load_dotenv()
    logger = configure_logging()

    try:
        # Pydantic will validate the inputs when creating the order via builder functions
        # We handle the 'str' to 'Decimal' conversion manually first to avoid Pydantic complaining if it's not a valid number
        try:
            parsed_quantity = Decimal(quantity) if quantity is not None else None
            parsed_price = Decimal(price) if price is not None else None
            parsed_stop_price = Decimal(stop_price) if stop_price is not None else None
        except Exception as e:
            raise ValueError(f"Numeric conversion error: {e}")

        # The builders create an OrderRequest and trigger Pydantic validation
        normalized_order_type = order_type.strip().upper()
        if normalized_order_type == "MARKET":
            order = build_market_order(symbol, side, parsed_quantity, client_order_id)
        elif normalized_order_type == "LIMIT":
            if parsed_price is None:
                raise ValueError("Price is required for LIMIT orders.")
            order = build_limit_order(
                symbol,
                side,
                parsed_quantity,
                parsed_price,
                time_in_force=time_in_force.upper(),
                client_order_id=client_order_id,
            )
        elif normalized_order_type == "STOP_MARKET":
            if parsed_stop_price is None:
                raise ValueError("Stop price is required for STOP_MARKET orders.")
            order = build_stop_market_order(
                symbol,
                side,
                parsed_quantity,
                parsed_stop_price,
                client_order_id=client_order_id,
            )
        else:
            raise ValueError(f"Unsupported order type: {order_type}")

        logger.info("Validated order request: %s", order.model_dump())

        if dry_run:
            _render_order_preview(order.to_api_payload(), title="Dry Run Payload")
            return

        client = BinanceFuturesTestnetClient.from_env()
        service = OrderService(client, logger=logger)
        response = service.submit(order)
        _render_order_result(response)
    except (ValidationError, ValueError) as exc:
        logger.warning("Validation failed: %s", exc)
        console.print(f"[red]Validation error:[/red] {exc}")
        raise typer.Exit(code=2)
    except RuntimeError as exc:
        logger.error("Configuration error: %s", exc)
        console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except BinanceAPIError as exc:
        logger.error("Binance API error: %s", exc)
        console.print(f"[red]Binance API error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except Exception as exc:  # pragma: no cover - safety net for CLI runtime errors
        logger.exception("Unexpected error while placing order")
        console.print(f"[red]Unexpected error:[/red] {exc}")
        raise typer.Exit(code=1) from exc


def _render_order_preview(payload: dict[str, str], title: str) -> None:
    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("Field", style="bold")
    table.add_column("Value")
    for key, value in payload.items():
        table.add_row(key, str(value))
    console.print(table)
    console.print("[yellow]Dry run only:[/yellow] no request was sent.")


def _render_order_result(response: dict[str, object]) -> None:
    table = Table(title="Order Submitted", show_header=True, header_style="bold green")
    table.add_column("Field", style="bold")
    table.add_column("Value")

    interesting_keys = ["orderId", "symbol", "status", "side", "type", "price", "avgPrice", "executedQty", "origQty", "clientOrderId"]
    for key in interesting_keys:
        if key in response:
            table.add_row(key, str(response[key]))

    if not table.rows:
        for key, value in response.items():
            table.add_row(str(key), str(value))

    console.print(table)
    console.print("[green]Order request completed successfully.[/green]")


@app.command()
def interactive() -> None:
    """Walk through order entry with prompts and validation."""

    load_dotenv()
    logger = configure_logging()

    console.print("[bold cyan]Interactive Binance Futures Testnet mode[/bold cyan]")
    
    symbol = questionary.text("Symbol (e.g. BTCUSDT):", default="BTCUSDT").ask()
    if not symbol:
        return
        
    try:
        client = BinanceFuturesTestnetClient.from_env()
        current_price = client.get_ticker_price(symbol)
        console.print(f"Current price of [bold green]{symbol}[/bold green]: {current_price}")
    except Exception as e:
        console.print(f"[yellow]Could not fetch current price for {symbol}: {e}[/yellow]")
        client = None

    side = questionary.select(
        "Side:",
        choices=["BUY", "SELL"]
    ).ask()
    if not side:
        return

    order_type = questionary.select(
        "Order type:",
        choices=["MARKET", "LIMIT", "STOP_MARKET"]
    ).ask()
    if not order_type:
        return

    quantity = questionary.text("Quantity:", default="0.001").ask()
    if not quantity:
        return

    price = None
    if order_type == "LIMIT":
        price = questionary.text("Limit price:").ask()

    stop_price = None
    if order_type == "STOP_MARKET":
        stop_price = questionary.text("Stop price:").ask()

    time_in_force = "GTC"
    if order_type == "LIMIT":
        time_in_force = questionary.select("Time in force:", choices=["GTC", "IOC", "FOK"]).ask()

    client_order_id = questionary.text("Client order id (optional):").ask()
    dry_run = questionary.confirm("Dry run only?", default=True).ask()
    if dry_run is None:
        return

    _submit_order(
        logger=logger,
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        stop_price=stop_price,
        time_in_force=time_in_force,
        client_order_id=client_order_id or None,
        dry_run=dry_run,
    )


def _submit_order(
    *,
    logger,
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: str | None,
    stop_price: str | None,
    time_in_force: str,
    client_order_id: str | None,
    dry_run: bool,
) -> None:
    try:
        try:
            parsed_quantity = Decimal(quantity) if quantity is not None else None
            parsed_price = Decimal(price) if price is not None else None
            parsed_stop_price = Decimal(stop_price) if stop_price is not None else None
        except Exception as e:
            raise ValueError(f"Numeric conversion error: {e}")

        normalized_order_type = order_type.strip().upper()
        if normalized_order_type == "MARKET":
            order = build_market_order(symbol, side, parsed_quantity, client_order_id)
        elif normalized_order_type == "LIMIT":
            if parsed_price is None:
                raise ValueError("Price is required for LIMIT orders.")
            order = build_limit_order(
                symbol,
                side,
                parsed_quantity,
                parsed_price,
                time_in_force=time_in_force.upper(),
                client_order_id=client_order_id,
            )
        elif normalized_order_type == "STOP_MARKET":
            if parsed_stop_price is None:
                raise ValueError("Stop price is required for STOP_MARKET orders.")
            order = build_stop_market_order(
                symbol,
                side,
                parsed_quantity,
                parsed_stop_price,
                client_order_id=client_order_id,
            )
        else:
            raise ValueError(f"Unsupported order type: {order_type}")

        logger.info("Validated order request: %s", order.model_dump())

        if dry_run:
            _render_order_preview(order.to_api_payload(), title="Dry Run Payload")
            return

        client = BinanceFuturesTestnetClient.from_env()
        service = OrderService(client, logger=logger)
        response = service.submit(order)
        _render_order_result(response)
    except (ValidationError, ValueError) as exc:
        logger.warning("Validation failed: %s", exc)
        console.print(f"[red]Validation error:[/red] {exc}")
        raise typer.Exit(code=2)
    except RuntimeError as exc:
        logger.error("Configuration error: %s", exc)
        console.print(f"[red]Configuration error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except BinanceAPIError as exc:
        logger.error("Binance API error: %s", exc)
        console.print(f"[red]Binance API error:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    except Exception as exc:  # pragma: no cover - safety net for CLI runtime errors
        logger.exception("Unexpected error while placing order")
        console.print(f"[red]Unexpected error:[/red] {exc}")
        raise typer.Exit(code=1) from exc


def main() -> None:
    app()


if __name__ == "__main__":
    main()
