import csv
from backend.data_loader import load_all_data

data = load_all_data()
with open('output.csv', encoding='utf-8') as f:
    preds = {r['request_id']: r for r in csv.DictReader(f)}

for rid in sorted(data.sample_outputs.keys(), key=lambda x: int(x.split('_')[1])):
    exp = data.sample_outputs[rid]
    pred = preds.get(rid, {})
    req = data.requests.get(rid)
    prof = data.profiles.get(req.user_id) if req else None
    u = req.user_id if req else ""
    cur = prof.home_currency if prof else ""
    amt = req.requested_amount if req else 0
    rdate = req.request_date if req else ""
    ddate = req.desired_completion_date if req else ""
    part = req.allows_partial_payment if req else ""
    
    print('=' * 85)
    print(f"REQ: {rid} | User: {u} ({cur}) | ReqAmt: {amt} | ReqDate: {rdate} | Deadline: {ddate} | Part: {part}")
    print(f"  EXP : status={exp.get('affordability_status')} | amt={exp.get('amount_safe_to_pay')} | method={exp.get('recommended_payment_method')} | date={exp.get('earliest_date_for_full_payment')} | plan={exp.get('payment_plan')} | chg={exp.get('spending_changes_needed')}")
    print(f"  PRED: status={pred.get('affordability_status')} | amt={pred.get('amount_safe_to_pay')} | method={pred.get('recommended_payment_method')} | date={pred.get('earliest_date_for_full_payment')} | plan={pred.get('payment_plan')} | chg={pred.get('spending_changes_needed')}")
