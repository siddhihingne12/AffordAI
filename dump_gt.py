import pandas as pd
df = pd.read_csv('dataset/sample_requests.csv')
for idx, row in df.iterrows():
    print(f"{row['request_id']} | u={row['user_id']} | amt={row['requested_amount']} | safe={row['amount_safe_to_pay']} | status={row['affordability_status']} | method={row['recommended_payment_method']} | date={row['earliest_date_for_full_payment']} | plan={row['payment_plan']} | chg={row['spending_changes_needed']}")
