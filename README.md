# Trading Bot for Binance Futures Testnet

Small Python 3.x CLI app for placing Market and Limit orders on Binance USDT-M Futures Testnet.

## Features

- **Order Types**: Market, Limit, and Stop Market (STOP_MARKET) orders
- **Validation**: Strict data validation using **Pydantic**
- **Interactive UI**: Beautiful, arrow-key navigable terminal UI using **Questionary** (fetches live ticker price!)
- **Sides**: BUY and SELL support
- **Logging**: Structured logging to console and file
- **Testing**: Comprehensive tests mocking the Binance API using **pytest** and **responses**
- **Safety**: `--dry-run` preview for safe checks

## Setup

1. Create a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

Optional, for a console command:

```bash
pip install -e .
```

3. Add testnet credentials to `.env`:

```env
BINANCE_API_KEY=your_testnet_key
BINANCE_API_SECRET=your_testnet_secret
BINANCE_BASE_URL=https://testnet.binancefuture.com
```

## Run

Use the CLI directly:

```bash
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

Or, use the **Interactive Mode** (recommended):

```bash
python cli.py interactive
```
*(This will launch a beautiful menu-driven wizard that also fetches the live ticker price!)*

If installed editable, use:

```bash
trading-bot place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

Limit order example:

```bash
python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 75000 --time-in-force GTC
```

Stop Market order example:

```bash
python cli.py place --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.001 --stop-price 70000
```

Dry run example:

```bash
python cli.py place --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.001 --price 70000 --dry-run
```

## Logging

Logs are written to `logs/trading_bot.log` and mirrored to the console.

## Tests

Run the comprehensive unit tests with `pytest` (API requests are mocked using `responses`):

```bash
pytest tests/
```
