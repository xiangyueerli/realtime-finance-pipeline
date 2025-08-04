import pandas as pd

df_permid = pd.read_csv("TRNA.Mapping.EN.PermId.Ticker.110.txt", sep="\t")
df_permid = df_permid.drop_duplicates("PermID")

df_tickers = pd.read_csv('stock_ticker.csv')
all_companies = pd.merge(df_tickers, df_permid, on="Ticker", how="right")

companies = all_companies[all_companies["Company Name"].isna()]

df_comp = pd.read_csv("TRNA.CMPNY.EN.BASIC.110.txt", sep="\t")
pd.merge(companies, df_comp, on="PermID").to_csv("unidentified_news_companies.csv", index=False)