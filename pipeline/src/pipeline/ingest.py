import requests
import pandas as pd

URL = "https://api.llama.fi/protocol/monarq"


def fetch_tvl() -> pd.DataFrame:
    resp = requests.get(URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    df = pd.DataFrame(data["tvl"])[["date", "totalLiquidityUSD"]]
    df["date"] = pd.to_datetime(df["date"], unit="s", utc=True)
    return df


if __name__ == "__main__":
    df = fetch_tvl()
    df.to_csv("monarq_tvl.csv", index=False)
    print(df.head())
    print(f"{len(df)} rows saved to monarq_tvl.csv")