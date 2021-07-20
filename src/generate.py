import datetime
import json
import re
import sys
from urllib import request

from dateutil.parser import isoparse
from dateutil.relativedelta import relativedelta
from mdutils.mdutils import MdUtils

conversation_rate_in_time_regex = re.compile(r"avg: [$€](?P<rate>\d+)", re.MULTILINE)


def get_coin_conversion_rate(fiat, date=None):
    # Request the converstion rate between BTC and the selected fiat currency
    url = f"https://{fiat}.rate.sx/"
    if date:
        date = isoparse(date)
        url += f"BTC@{date.strftime('%Y-%m-%d+%Hh%Mm%Ss')}" \
               f"?T&q"
    else:
        url += "1BTC"

    with request.urlopen(url) as connection:
        conversion = connection.read().decode("utf-8")
        if date:
            return float(conversation_rate_in_time_regex.search(conversion)["rate"])
        else:
            return float(conversion)


def get_fiat_conversion_rate(fiat_a, fiat_b, date=None):
    # Request frankfurter.app for the converstion rate between two currencies.
    #
    # Parameters:
    #   fiat_a: Fiat A (to convert from)
    #   fiat_b: Fiat B (to convert two)
    #   date:
    #     If specified, requests the converstion rate between the two given currencies at the given 
    # 
    url = f"https://api.frankfurter.app"
    if date:
        date = isoparse(date)
        url += f"/{date.strftime('%Y-%m-%d')}"
    else:
        url += "/latest"
    url += f"?from={fiat_a}&to={fiat_b}"
    with request.urlopen(url) as connection:
        return json.load(connection)["rates"][fiat_b.upper()]


current_time = datetime.datetime.utcnow()
with open("src/known-data.json", "r") as file:
    known_data = json.load(file)
new_transparency_data = json.loads(sys.argv[1])

# Calculate new funds
current_funds = known_data["total_current_btc_funds"] + new_transparency_data["new_btc_previous_month"]
for bounty in new_transparency_data["bounty_costs"]:
    current_funds - float(bounty["bounty_cost_crypto"].strip(" BTC"))

usd_to_btc = get_coin_conversion_rate("usd")
eur_to_btc = get_coin_conversion_rate("eur")
btc_price_str = f"~€{round(eur_to_btc, 2)} or \~${round(usd_to_btc, 2)}"

# Create header
md = MdUtils(file_name=f"finance/{(current_time - relativedelta(months=1)).strftime('%Y-%m')}.md")
md.new_header(level=1, title=f"Finances for {(current_time - relativedelta(months=1)).strftime('%B %Y')}")

# Donations section
md.new_header(level=2, title="Donations:")
if not new_transparency_data["new_btc_previous_month"]:
    md.new_paragraph("Bitcoin (BTC): None")
else:
    md.new_paragraph(f"Bitcoin (BTC): {new_transparency_data['new_btc_previous_month']} BTC worth"
                     f" ~€{round(new_transparency_data['new_btc_previous_month'] * eur_to_btc, 2)}"
                     f" at the time of publishing (Bitcoin price {btc_price_str})")

md.new_paragraph("Monero (XMR): X XMR worth ~€X at the time of publishing (Monero price \~€X or \~$X)")

md.new_header(level=2, title="Expenses:")
for bounty in new_transparency_data["bounty_costs"]:
    usd_to_btc_rate_at_time = get_coin_conversion_rate("usd", date=bounty['date'])
    usd_to_eur_rate_at_time = get_fiat_conversion_rate("usd", "eur", date=bounty['date'])
    usd_bounty_cost = float(bounty['bounty_cost_crypto'].strip(' BTC')) * usd_to_btc_rate_at_time

    md.new_paragraph(f"Bounty ({bounty['url']}): {bounty['bounty_cost_crypto']} worth ~ "
                     f"€{round(usd_bounty_cost * usd_to_eur_rate_at_time, 2)} (~${round(usd_bounty_cost, 2)})")

md.new_header(level=2, title="Current funds:")
md.new_paragraph(f"Bitcoin (BTC): {current_funds} BTC worth ~€{round(current_funds * eur_to_btc, 2)} "
                 f"(\~${round(current_funds * usd_to_btc, 2)}) at the time of publishing "
                 f"(Bitcoin price {btc_price_str})")

md.new_paragraph("Monero (XMR): X XMR worth ~€X (\~$X) at the time of publishing (Monero price ~€X or \~$X)")
md.create_md_file()

# Now we update the known data
known_data["total_current_btc_funds"] = current_funds
with open("src/known-data.json", "w") as file:
    json.dump(known_data, file)
