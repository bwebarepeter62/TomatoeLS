-- ==========================================================
-- Tomato Leaf Scan — SQLite Relational Database Schema
-- File: web-app/database/schema.sql
-- ==========================================================

PRAGMA foreign_keys = ON;

-- Table: farms
-- Stores tomato farm plot registries and cultivation metadata
CREATE TABLE IF NOT EXISTS farms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    location TEXT DEFAULT '',
    size TEXT DEFAULT '',
    variety TEXT DEFAULT '',
    planting_date TEXT DEFAULT '',
    plant_count INTEGER DEFAULT 0,
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: scans
-- Stores leaf inspection photos, AI predictions, and agronomic diagnostic records
CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    farm_id INTEGER,
    farm_name TEXT DEFAULT 'General / Unassigned',
    image_filename TEXT NOT NULL,
    prediction_label TEXT NOT NULL,
    is_healthy INTEGER DEFAULT 0,
    confidence REAL DEFAULT 0.0,
    disease_name TEXT,
    disease_type TEXT,
    disease_summary TEXT,
    disease_cause TEXT,
    raw_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(farm_id) REFERENCES farms(id) ON DELETE SET NULL
);

-- Indexes for high-performance dashboard aggregation and search queries
CREATE INDEX IF NOT EXISTS idx_scans_farm_id ON scans(farm_id);
CREATE INDEX IF NOT EXISTS idx_scans_created_at ON scans(created_at);
CREATE INDEX IF NOT EXISTS idx_scans_is_healthy ON scans(is_healthy);
