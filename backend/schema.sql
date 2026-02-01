-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Projects Table
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL, -- References auth.users provided by Supabase
    name TEXT NOT NULL,
    source_url TEXT,
    status TEXT DEFAULT 'pending', -- pending, downloading, processing, completed, error
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Clips Table
CREATE TABLE clips (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    start_time FLOAT NOT NULL,
    end_time FLOAT NOT NULL,
    video_path TEXT, -- Path to the generated 9:16 clip
    transcript JSONB, -- Stored transcript for this clip
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
