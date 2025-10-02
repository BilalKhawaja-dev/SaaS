-- Demo data for testing and development
-- This migration inserts sample data for demonstration purposes

-- Insert demo tenants
INSERT INTO tenants (id, company_name, plan, status) VALUES 
    ('550e8400-e29b-41d4-a716-446655440001', 'Demo Corp', 'pro', 'active'),
    ('550e8400-e29b-41d4-a716-446655440002', 'Test Inc', 'basic', 'active'),
    ('550e8400-e29b-41d4-a716-446655440003', 'Enterprise Ltd', 'enterprise', 'active')
ON CONFLICT (id) DO NOTHING;

-- Insert demo users
INSERT INTO users (id, tenant_id, email, password_hash, role) VALUES 
    ('660e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440001', 'admin@democorp.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.PmvlG.', 'admin'),
    ('660e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440002', 'user@testinc.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.PmvlG.', 'user'),
    ('660e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440003', 'readonly@enterpriseltd.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.PmvlG.', 'readonly')
ON CONFLICT (email) DO NOTHING;

-- Insert demo subscriptions
INSERT INTO subscriptions (tenant_id, plan, status, billing_cycle, amount, next_billing_date) VALUES 
    ('550e8400-e29b-41d4-a716-446655440001', 'pro', 'active', 'monthly', 99.00, CURRENT_DATE + INTERVAL '30 days'),
    ('550e8400-e29b-41d4-a716-446655440002', 'basic', 'active', 'monthly', 29.00, CURRENT_DATE + INTERVAL '30 days'),
    ('550e8400-e29b-41d4-a716-446655440003', 'enterprise', 'active', 'yearly', 2988.00, CURRENT_DATE + INTERVAL '365 days')
ON CONFLICT DO NOTHING;

-- Insert demo accounts
INSERT INTO accounts (tenant_id, balance, currency) VALUES 
    ('550e8400-e29b-41d4-a716-446655440001', 1500.00, 'USD'),
    ('550e8400-e29b-41d4-a716-446655440002', 750.00, 'USD'),
    ('550e8400-e29b-41d4-a716-446655440003', 5000.00, 'USD')
ON CONFLICT DO NOTHING;

-- Insert demo transactions
INSERT INTO transactions (tenant_id, account_id, amount, transaction_type, description) 
SELECT 
    t.id as tenant_id,
    a.id as account_id,
    CASE 
        WHEN t.plan = 'basic' THEN -29.00
        WHEN t.plan = 'pro' THEN -99.00
        WHEN t.plan = 'enterprise' THEN -299.00
    END as amount,
    'debit' as transaction_type,
    'Monthly subscription fee' as description
FROM tenants t
JOIN accounts a ON t.id = a.tenant_id
WHERE NOT EXISTS (
    SELECT 1 FROM transactions tr 
    WHERE tr.tenant_id = t.id 
    AND tr.description = 'Monthly subscription fee'
);

-- Insert additional demo transactions
INSERT INTO transactions (tenant_id, account_id, amount, transaction_type, description) 
SELECT 
    t.id as tenant_id,
    a.id as account_id,
    1000.00 as amount,
    'credit' as transaction_type,
    'Initial account credit' as description
FROM tenants t
JOIN accounts a ON t.id = a.tenant_id
WHERE NOT EXISTS (
    SELECT 1 FROM transactions tr 
    WHERE tr.tenant_id = t.id 
    AND tr.description = 'Initial account credit'
);