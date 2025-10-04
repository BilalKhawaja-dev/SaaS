-- Demo data for testing and development
-- This migration inserts sample data for demonstration purposes

-- Insert demo tenants with proper UUID handling
INSERT INTO tenants (id, company_name, plan, status, created_at, updated_at) VALUES 
    ('550e8400-e29b-41d4-a716-446655440001'::uuid, 'Demo Corp', 'pro', 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('550e8400-e29b-41d4-a716-446655440002'::uuid, 'Test Inc', 'basic', 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('550e8400-e29b-41d4-a716-446655440003'::uuid, 'Enterprise Ltd', 'enterprise', 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (id) DO NOTHING;

-- Insert demo users with proper UUID handling
INSERT INTO users (id, tenant_id, email, password_hash, role, created_at, updated_at) VALUES 
    ('660e8400-e29b-41d4-a716-446655440001'::uuid, '550e8400-e29b-41d4-a716-446655440001'::uuid, 'admin@democorp.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.PmvlG.', 'admin', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('660e8400-e29b-41d4-a716-446655440002'::uuid, '550e8400-e29b-41d4-a716-446655440002'::uuid, 'user@testinc.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.PmvlG.', 'user', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('660e8400-e29b-41d4-a716-446655440003'::uuid, '550e8400-e29b-41d4-a716-446655440003'::uuid, 'readonly@enterpriseltd.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.PmvlG.', 'readonly', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (email) DO NOTHING;

-- Insert demo subscriptions with proper UUID handling
INSERT INTO subscriptions (tenant_id, plan, status, billing_cycle, amount, next_billing_date, created_at, updated_at) VALUES 
    ('550e8400-e29b-41d4-a716-446655440001'::uuid, 'pro', 'active', 'monthly', 99.00, CURRENT_DATE + INTERVAL '30 days', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('550e8400-e29b-41d4-a716-446655440002'::uuid, 'basic', 'active', 'monthly', 29.00, CURRENT_DATE + INTERVAL '30 days', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('550e8400-e29b-41d4-a716-446655440003'::uuid, 'enterprise', 'active', 'yearly', 2988.00, CURRENT_DATE + INTERVAL '365 days', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (id) DO NOTHING;

-- Insert demo accounts with proper UUID handling
INSERT INTO accounts (tenant_id, balance, currency, created_at, updated_at) VALUES 
    ('550e8400-e29b-41d4-a716-446655440001'::uuid, 1500.00, 'USD', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('550e8400-e29b-41d4-a716-446655440002'::uuid, 750.00, 'USD', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('550e8400-e29b-41d4-a716-446655440003'::uuid, 5000.00, 'USD', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (id) DO NOTHING;

-- Insert demo transactions with proper UUID handling
INSERT INTO transactions (tenant_id, account_id, amount, transaction_type, description, created_at) 
SELECT 
    t.id as tenant_id,
    a.id as account_id,
    CASE 
        WHEN t.plan = 'basic' THEN -29.00
        WHEN t.plan = 'pro' THEN -99.00
        WHEN t.plan = 'enterprise' THEN -299.00
    END as amount,
    'debit' as transaction_type,
    'Monthly subscription fee' as description,
    CURRENT_TIMESTAMP as created_at
FROM tenants t
JOIN accounts a ON t.id = a.tenant_id
WHERE NOT EXISTS (
    SELECT 1 FROM transactions tr 
    WHERE tr.tenant_id = t.id 
    AND tr.description = 'Monthly subscription fee'
);

-- Insert additional demo transactions
INSERT INTO transactions (tenant_id, account_id, amount, transaction_type, description, created_at) 
SELECT 
    t.id as tenant_id,
    a.id as account_id,
    1000.00 as amount,
    'credit' as transaction_type,
    'Initial account credit' as description,
    CURRENT_TIMESTAMP as created_at
FROM tenants t
JOIN accounts a ON t.id = a.tenant_id
WHERE NOT EXISTS (
    SELECT 1 FROM transactions tr 
    WHERE tr.tenant_id = t.id 
    AND tr.description = 'Initial account credit'
);