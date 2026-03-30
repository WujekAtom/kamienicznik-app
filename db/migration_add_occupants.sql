-- Migration: add occupants column to tenants
-- Run once: docker compose exec db psql -U rental -d rental -f /dev/stdin << 'SQL'
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS occupants INTEGER NOT NULL DEFAULT 1;
-- SQL
