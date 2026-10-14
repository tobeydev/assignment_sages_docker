import os

from sqlalchemy import create_engine

from pipeline.ingest import fetch_tvl

# Matches the docker run command you used for Postgres.
# Override with environment variables when running in a container.
DB_USER = os.getenv("POSTGRES_USER", "tobey")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "root")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "data-set")

TABLE_NAME = "monarq_tvl"


def load_to_postgres(df) -> None:
    engine = create_engine(
        f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    df.to_sql(TABLE_NAME, con=engine, if_exists="replace", index=False)


def main() -> None:
    print("Fetching Monarq TVL from DefiLlama...")
    df = fetch_tvl()
    print(f"Fetched {len(df)} rows. Loading into PostgreSQL...")
    load_to_postgres(df)
    print(f"Ingestion complete! Data loaded into table '{TABLE_NAME}'.")


if __name__ == "__main__":
    main()