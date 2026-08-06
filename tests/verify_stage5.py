import json
from app.services.pii_masker import DataSanitizer, sanitize_transactions

def test_pii_masking():
    print("=== STEP 1: Testing Direct Text Sanitization ===")
    sample_text_1 = "Payment to John Doe in New York acc 987654321"
    masked_1 = DataSanitizer.sanitize_text(sample_text_1)
    print("Original 1:", sample_text_1)
    print("Masked 1  :", masked_1)
    assert "[USER_MASKED]" in masked_1 or "John Doe" not in masked_1
    assert "[LOCATION_MASKED]" in masked_1 or "New York" not in masked_1
    assert "[ACCOUNT_MASKED]" in masked_1

    print("\n=== STEP 2: Testing Transaction List Deep Copy Sanitization ===")
    raw_transactions = [
        {"date": "2026-08-01", "amount": 45.0, "category": "John Doe transfer ACC1234567"},
        {"date": "2026-08-02", "amount": 14.99, "category": "Netflix San Francisco CA"}
    ]
    
    masked_transactions = sanitize_transactions(raw_transactions)
    
    print("Original Data (Unchanged):", json.dumps(raw_transactions, indent=2))
    print("\nMasked Payload (Sent to LLM):", json.dumps(masked_transactions, indent=2))

    # Assert deep copy integrity (original data untouched)
    assert raw_transactions[0]["category"] == "John Doe transfer ACC1234567"
    assert raw_transactions[1]["category"] == "Netflix San Francisco CA"
    
    # Assert masking logic
    assert "[ACCOUNT_MASKED]" in masked_transactions[0]["category"]
    
    print("\n✅ STAGE 5 PII MASKING VERIFICATION PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_pii_masking()
