"""
Evaluate the deterministic engine + message adjustments against all 25 ground-truth samples.
Uses the full pipeline (with message parsing) but skips LLM explanation.
"""
import sys, csv, time
sys.stdout.reconfigure(encoding='utf-8')

from backend.data_loader import load_all_data
from backend.models import AgentDecision
from backend.profile_builder import build_safety_twin
from backend.strategy_simulator import evaluate_all_strategies, select_best_strategy
from backend.safety_engine import validate_strategy, determine_affordability_status
from backend.evidence_extractor import parse_all_messages
from backend.utils import format_payment_plan

data = load_all_data()

# Parse all messages for adjustments
print("Parsing messages...")
try:
    message_adjustments = parse_all_messages(data)
    adj_count = sum(len(v) for v in message_adjustments.values())
    print(f"  Got {adj_count} adjustments for {len(message_adjustments)} users")
except Exception as e:
    print(f"  Message parsing failed: {e}")
    message_adjustments = {}

# Load ground truth
gt = {}
with open('dataset/sample_requests.csv', 'r', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        gt[row['request_id']] = row

sample_ids = sorted(gt.keys(), key=lambda x: int(x.split('_')[1]))

print(f"\n{'Request':<12} {'GT Status':<22} {'Pred Status':<22} {'Status':>7}  {'GT Method':<18} {'Pred Method':<18} {'Method':>7}")
print('-' * 120)

status_correct = 0
method_correct = 0
results = []

start = time.time()
for rid in sample_ids:
    req = data.requests.get(rid)
    if not req:
        continue

    user_adjustments = message_adjustments.get(req.user_id, [])
    twin = build_safety_twin(req.user_id, req.request_date, data, message_adjustments=user_adjustments)
    opts = data.payment_options_by_request.get(rid, [])
    strats = evaluate_all_strategies(twin, req, opts, data)
    for s in strats:
        validate_strategy(s, twin, req)
    best = select_best_strategy(strats, twin, req)
    
    status = determine_affordability_status(best, req)
    method = best.payment_method
    plan = format_payment_plan(best.payment_plan)
    safe = min(best.amount_safe_to_pay, req.requested_amount)
    
    gt_status = gt[rid]['affordability_status']
    gt_method = gt[rid]['recommended_payment_method']
    gt_safe = float(gt[rid]['amount_safe_to_pay'])
    gt_plan = gt[rid]['payment_plan']
    
    s_ok = status == gt_status
    m_ok = method == gt_method
    
    if s_ok: status_correct += 1
    if m_ok: method_correct += 1
    
    s_mark = 'OK' if s_ok else 'MISS'
    m_mark = 'OK' if m_ok else 'MISS'
    
    print(f"  {rid:<10} {gt_status:<22} {status:<22} {s_mark:>7}  {gt_method:<18} {method:<18} {m_mark:>7}")
    
    results.append({
        'rid': rid, 'gt_status': gt_status, 'pred_status': status,
        'gt_method': gt_method, 'pred_method': method,
        'gt_safe': gt_safe, 'pred_safe': round(safe, 2),
        'gt_plan': gt_plan, 'pred_plan': plan,
        'status_ok': s_ok, 'method_ok': m_ok,
    })

elapsed = time.time() - start
n = len(results)
print(f"\n{'='*120}")
print(f"STATUS accuracy:  {status_correct}/{n} = {status_correct/n:.0%}")
print(f"METHOD accuracy:  {method_correct}/{n} = {method_correct/n:.0%}")
print(f"Time: {elapsed:.2f}s ({elapsed/n:.3f}s each)")

# Show mismatches in detail
misses = [r for r in results if not r['status_ok'] or not r['method_ok']]
if misses:
    print(f"\n=== MISMATCHES ({len(misses)}) ===")
    for r in misses:
        print(f"\n  {r['rid']}:")
        if not r['status_ok']:
            print(f"    Status: GT={r['gt_status']}  Pred={r['pred_status']}")
        if not r['method_ok']:
            print(f"    Method: GT={r['gt_method']}  Pred={r['pred_method']}")
        print(f"    Safe:   GT={r['gt_safe']}  Pred={r['pred_safe']}")
        print(f"    Plan:   GT={r['gt_plan']}")
        print(f"    Plan:   PR={r['pred_plan']}")
