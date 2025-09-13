-- init-data.sql
-- SQL file to initialize default data for authentication system

-- Create roles table
CREATE TABLE IF NOT EXISTS roles (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    permissions TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_roles_name (name)
);

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    role_id INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE RESTRICT,
    INDEX idx_users_username (username),
    INDEX idx_users_email (email)
);

-- Insert default roles
INSERT IGNORE INTO roles (name, description, permissions) VALUES 
(
    'admin', 
    'Administrator with full system access',
    '["user.create", "user.read", "user.update", "user.delete", "role.create", "role.read", "role.update", "role.delete", "workload.create", "workload.read", "workload.update", "workload.delete", "rule.create", "rule.read", "rule.update", "rule.delete", "server.create", "server.read", "server.update", "server.delete", "dashboard.read", "schedule.read", "schedule.update"]'
),
(
    'user', 
    'Regular user with limited permissions',
    '["workload.read", "rule.read", "server.read", "dashboard.read", "schedule.read"]'
);

-- Insert default users
-- Password hash for "admin123" = $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewmyUj6mhKdKNhOi
-- Password hash for "manager123" = $2b$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi
-- Password hash for "user123" = $2b$12$wa2+1RKjh1PBDT2o2C0pPeKVT6zQzP8AkCfSQCIkVjy1ZjBxJEzaK

INSERT IGNORE INTO users (username, email, password_hash, full_name, role_id, is_active) VALUES 
(
    'admin', 
    'admin@company.com', 
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewmyUj6mhKdKNhOi',
    'System Administrator', 
    (SELECT id FROM roles WHERE name = 'admin'), 
    TRUE
),
(
    'manager1', 
    'manager1@company.com', 
    '$2b$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi',
    'John Manager', 
    (SELECT id FROM roles WHERE name = 'admin'), 
    TRUE
),
(
    'user1', 
    'user1@company.com', 
    '$2b$12$wa2+1RKjh1PBDT2o2C0pPeKVT6zQzP8AkCfSQCIkVjy1ZjBxJEzaK',
    'Alice Smith', 
    (SELECT id FROM roles WHERE name = 'user'), 
    TRUE
),
(
    'user2', 
    'user2@company.com', 
    '$2b$12$wa2+1RKjh1PBDT2o2C0pPeKVT6zQzP8AkCfSQCIkVjy1ZjBxJEzaK',
    'Bob Johnson', 
    (SELECT id FROM roles WHERE name = 'user'), 
    TRUE
),
(
    'user3', 
    'user3@company.com', 
    '$2b$12$wa2+1RKjh1PBDT2o2C0pPeKVT6zQzP8AkCfSQCIkVjy1ZjBxJEzaK',
    'Charlie Brown', 
    (SELECT id FROM roles WHERE name = 'user'), 
    FALSE
);