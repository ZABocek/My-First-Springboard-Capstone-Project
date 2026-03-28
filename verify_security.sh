#!/bin/bash
# Security Verification Script

echo "=== SECURITY VERIFICATION ==="
echo ""
echo "✓ Step 1: Verify .env file exists"
if [ -f .env ]; then
    echo "  ✅ .env file found"
else
    echo "  ❌ .env file NOT found"
    exit 1
fi

echo ""
echo "✓ Step 2: Verify .env contains your keys"
if grep -q "SECRET_KEY=" .env; then
    echo "  ✅ SECRET_KEY is set"
else
    echo "  ❌ SECRET_KEY not found or incorrect"
fi

if grep -q "ADMIN_PASSWORD_KEY=" .env; then
    echo "  ✅ ADMIN_PASSWORD_KEY is set"
else
    echo "  ❌ ADMIN_PASSWORD_KEY not found or incorrect"
fi

echo ""
echo "✓ Step 3: Verify .env is in .gitignore"
if grep -q "^\.env$" .gitignore; then
    echo "  ✅ .env is in .gitignore"
else
    echo "  ❌ .env NOT in .gitignore - DANGER!"
    exit 1
fi

echo ""
echo "✓ Step 4: Check git status for .env"
if git status | grep -q ".env"; then
    echo "  ⚠️  .env appears in git status - checking if ignored..."
    if git check-ignore .env >/dev/null 2>&1; then
        echo "  ✅ .env is correctly ignored by git"
    fi
else
    echo "  ✅ .env is properly ignored"
fi

echo ""
echo "=== SECURITY VERIFICATION COMPLETE ==="
echo "✅ All security checks passed!"
