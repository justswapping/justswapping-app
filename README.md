# JustSwapping

A lightweight, privacy-focused cryptocurrency swap aggregator. JustSwapping lets users exchange one cryptocurrency for another without an account or registration. It fetches quotes from multiple instant-exchange providers (currently ChangeNOW and Godex) and routes the swap through whichever offers the better rate.

JustSwapping never holds user funds. Deposits go directly to the provider's deposit address, and the provider sends the swapped coins to the user's receiving address.

**Live instance:** [justswapping.io](https://justswapping.io) (run by the original author; see "Fees" below)

## Why this exists

This project began as a self-learning exercise by a former maths teacher teaching himself software development. It is shared openly in the hope that it is useful, and that others will review it, improve it, and run their own instances.

## Features

- No account required
- Compares quotes from multiple providers and picks the best rate
- Real-time swap status tracking
- Optional email receipts
- Refund address support
- Mobile-friendly interface

## Fees and affiliate programs

Both providers offer affiliate/partner programs:

- **ChangeNOW:** commission is linked to the partner account that owns the API key and is set on ChangeNOW's side. There is no commission setting in this code.
- **Godex:** the optional `GODEX_AFFILIATE_ID` setting attaches an affiliate ID to swaps. Leave it blank for none.

If you run your own instance, you decide whether to earn a commission. The live instance at justswapping.io earns affiliate commission from both providers ([0.4]% on ChangeNOW swaps and [0.45]% on Godex swaps). It is included in the rate shown to users, so you may get a slightly better rate going to a provider directly.

## Privacy notes

- JustSwapping does not require KYC, but **the providers may place swaps on hold for review** under their own policies. Always provide a refund address.
- The optional email address is used to send receipts. It is shared with ChangeNOW **only if no refund address is given**, so ChangeNOW can contact the user to return their funds if a swap fails.
- Each swap has a random access token, so only the browser that created a swap can view its details.
- The database stores swap details (coins, amounts, deposit, receiving and refund addresses, optional email) so swaps can be tracked.
- Quote and swap requests are sent from the server to the providers' APIs, so providers see the server's IP address, not the user's. Users still connect to the web server itself.

## Tech stack

- **Backend:** Python (Flask)
- **Server:** Gunicorn + Nginx
- **Database:** SQLite
- **Frontend:** HTML/CSS/JS (server-rendered templates)

## Project structure

```
├── app.py              # Main Flask application
├── engine_helpers/     # Swap lifecycle logic and helpers
├── models/             # Data models
├── providers/          # Provider integrations (ChangeNOW, Godex, mock)
├── static/             # CSS, JS, images
├── templates/          # HTML templates
├── tools/              # Development and diagnostic scripts
├── .env.example        # Configuration template
└── requirements.txt    # Python dependencies
```

## Running locally

1. Clone the repository.
2. Create and activate a virtual environment:

```
   python -m venv venv
   venv\Scripts\activate        # Windows
   source venv/bin/activate     # macOS/Linux
```

3. Install dependencies:

```
   pip install -r requirements.txt
```

4. Copy `.env.example` to `.env` and fill in your own API keys. Every setting is explained in the file. Never commit your `.env`.
5. Run the app:

```
   python app.py
```

6. Visit `http://127.0.0.1:5000`

To try the interface without making real swaps, set `JUSTSWAPPING_DEV=1` in `.env` and leave both API keys blank. This enables a mock provider with fake quotes and a fake deposit address. **Never enable development mode on a live server.**

## Contributing

Code review, bug reports, security findings and pull requests are all very welcome. If you find a security issue, please report it privately first (see the contact address on the live site) rather than opening a public issue.

## Legal

Operating a public swap service may be regulated in your country. Running your own instance is your own responsibility.

## License

MIT. See [LICENSE](LICENSE).