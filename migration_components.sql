-- Migration: electricity_components, gas_components, water_advance on tenants
-- Run once:
-- docker compose exec db psql -U rental -d rental < migration_components.sql

-- Electricity components table
CREATE TABLE IF NOT EXISTS electricity_components (
    id SERIAL PRIMARY KEY,
    valid_from DATE NOT NULL,
    valid_to DATE,
    notes TEXT,
    var_rate NUMERIC(10,6) NOT NULL DEFAULT 0,
    extra_trade_cycle NUMERIC(10,4) NOT NULL DEFAULT 0,
    fixed_price NUMERIC(10,4) NOT NULL DEFAULT 0,
    dist_fixed NUMERIC(10,4) NOT NULL DEFAULT 0,
    transition_fee NUMERIC(10,6) NOT NULL DEFAULT 0,
    abonament NUMERIC(10,4) NOT NULL DEFAULT 0,
    power_fee NUMERIC(10,4) NOT NULL DEFAULT 0,
    quality_rate NUMERIC(10,6) NOT NULL DEFAULT 0,
    dist_variable NUMERIC(10,6) NOT NULL DEFAULT 0,
    oze_rate NUMERIC(10,6) NOT NULL DEFAULT 0,
    cogen_rate NUMERIC(10,6) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Gas components table
CREATE TABLE IF NOT EXISTS gas_components (
    id SERIAL PRIMARY KEY,
    valid_from DATE NOT NULL,
    valid_to DATE,
    notes TEXT,
    abonament NUMERIC(10,4) NOT NULL DEFAULT 0,
    conv_factor NUMERIC(10,6) NOT NULL DEFAULT 11.0,
    gas_price_per_kwh NUMERIC(10,6) NOT NULL DEFAULT 0,
    vat_pct NUMERIC(5,2) NOT NULL DEFAULT 23,
    dist_fixed NUMERIC(10,4) NOT NULL DEFAULT 0,
    dist_variable NUMERIC(10,6) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Water advance on tenants
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS water_advance NUMERIC(10,2) NOT NULL DEFAULT 0;
