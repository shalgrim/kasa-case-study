#!/usr/bin/env bash
# Smoke tests for the live deployed API.
# Usage: ./verify_live.sh [BASE_URL]
# Example: ./verify_live.sh https://kasa-case-study.onrender.com
#
# Registers a test user, uploads the CSV, and verifies scoring.
# Safe to run multiple times (register will fail on duplicate, but login works).

set -e

BASE_URL="${1:-https://kasa-case-study.onrender.com}"
CSV_FILE="${2:-../Example_Review_Comparison.csv}"
EMAIL="verify-$(date +%s)@test.com"
PASSWORD="testpass123"

echo "=== Verifying $BASE_URL ==="

echo -n "Health check... "
curl -sf "$BASE_URL/api/health" | python3 -c "import sys,json; assert json.load(sys.stdin)['status']=='ok'; print('OK')"

echo -n "Register user... "
TOKEN=$(curl -sf -X POST "$BASE_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "OK"

AUTH="Authorization: Bearer $TOKEN"

echo -n "Authenticated hotel list (pre-import)... "
COUNT=$(curl -sf "$BASE_URL/api/hotels" -H "$AUTH" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
echo "OK ($COUNT hotels)"

if [ -f "$CSV_FILE" ]; then
  echo -n "CSV import... "
  IMPORTED=$(curl -sf -X POST "$BASE_URL/api/hotels/import-csv" \
    -H "$AUTH" \
    -F "file=@$CSV_FILE" | python3 -c "import sys,json; print(json.load(sys.stdin)['imported'])")
  echo "OK ($IMPORTED rows imported)"

  echo -n "Hotel list (post-import)... "
  COUNT=$(curl -sf "$BASE_URL/api/hotels" -H "$AUTH" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
  echo "OK ($COUNT hotels)"

  echo -n "Scoring check (Sea Crest)... "
  SEA_CREST_ID=$(curl -sf "$BASE_URL/api/hotels" -H "$AUTH" | python3 -c "
import sys, json
hotels = json.load(sys.stdin)
sc = next((h for h in hotels if 'Sea Crest' in h['name']), None)
assert sc, 'Sea Crest not found'
s = sc['latest_snapshot']
assert s['google_normalized'] == 8.0, f'Google norm: {s[\"google_normalized\"]}'
assert s['booking_normalized'] == 7.3, f'Booking norm: {s[\"booking_normalized\"]}'
assert s['tripadvisor_normalized'] == 7.1, f'TA norm: {s[\"tripadvisor_normalized\"]}'
assert 7.5 <= s['weighted_average'] <= 7.7, f'WA: {s[\"weighted_average\"]}'
print(sc['id'])
")
  echo "OK (ID=$SEA_CREST_ID, normalized scores and weighted average correct)"

  echo -n "Hotel detail endpoint... "
  curl -sf "$BASE_URL/api/hotels/$SEA_CREST_ID" -H "$AUTH" | python3 -c "
import sys, json
h = json.load(sys.stdin)
assert h['name'] and 'Sea Crest' in h['name'], f'Wrong hotel: {h[\"name\"]}'
assert h['latest_snapshot'] is not None, 'No snapshot on detail'
print('OK (' + h['name'] + ')')
"

  echo -n "Hotel history endpoint... "
  curl -sf "$BASE_URL/api/hotels/$SEA_CREST_ID/history" -H "$AUTH" | python3 -c "
import sys, json
snapshots = json.load(sys.stdin)
assert isinstance(snapshots, list), f'Expected list, got {type(snapshots)}'
assert len(snapshots) >= 1, f'Expected >=1 snapshot, got {len(snapshots)}'
print('OK (' + str(len(snapshots)) + ' snapshots)')
"

  echo -n "CSV export endpoint... "
  EXPORT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/export/hotels" -H "$AUTH")
  if [ "$EXPORT_STATUS" = "200" ]; then
    echo "OK (HTTP 200)"
  else
    echo "FAIL (HTTP $EXPORT_STATUS)"
    exit 1
  fi
else
  echo "Skipping CSV tests (file not found: $CSV_FILE)"
fi

echo ""
echo "=== All checks passed ==="
