import pandas as pd

df1 = pd.read_csv("data/exams/mona.csv")
df2 = pd.read_csv("data/exams/ziga.csv")

df2 = df2[df1.columns]

out = pd.concat([df1, df2], ignore_index=True)
out.to_csv("data/exams/final_exams_schedule.csv", index=False)
