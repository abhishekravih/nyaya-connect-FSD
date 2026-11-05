-- ============================================================
-- NyayaConnect Relational Database Schema
-- Person 2: Backend Architect & Database Engineer
-- Target: MySQL Workbench 8.0+ / PostgreSQL / Cloud DB
-- ============================================================

-- 1. Users Table (Clients & Lawyers)
CREATE TABLE IF NOT EXISTS users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    role ENUM('CLIENT', 'LAWYER') NOT NULL DEFAULT 'CLIENT',
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Lawyers Table
CREATE TABLE IF NOT EXISTS lawyers (
    lawyer_id INT PRIMARY KEY AUTO_INCREMENT,
    full_name VARCHAR(120) NOT NULL,
    bar_council_id VARCHAR(50) UNIQUE NOT NULL,
    category ENUM('Civil', 'Consumer', 'Criminal') NOT NULL,
    experience_years INT NOT NULL,
    languages VARCHAR(150) NOT NULL,
    city VARCHAR(80) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(120) NOT NULL,
    consultation_fee DECIMAL(10, 2) NOT NULL,
    drafting_fee DECIMAL(10, 2) NOT NULL,
    hearing_fee DECIMAL(10, 2) NOT NULL,
    full_case_estimate DECIMAL(10, 2) NOT NULL,
    rating DECIMAL(3, 2) DEFAULT 4.50,
    INDEX idx_category (category),
    INDEX idx_city (city),
    INDEX idx_full_case_estimate (full_case_estimate)
);

-- 3. Bookings Table
CREATE TABLE IF NOT EXISTS bookings (
    booking_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    lawyer_id INT NOT NULL,
    case_category ENUM('Civil', 'Consumer', 'Criminal') NOT NULL,
    case_summary TEXT NOT NULL,
    total_agreed_fee DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (lawyer_id) REFERENCES lawyers(lawyer_id) ON DELETE RESTRICT,
    INDEX idx_user_id (user_id),
    INDEX idx_lawyer_id (lawyer_id)
);

-- 4. Case Milestones Table (4 Sequential Linked Stages)
CREATE TABLE IF NOT EXISTS case_milestones (
    milestone_id INT PRIMARY KEY AUTO_INCREMENT,
    booking_id INT NOT NULL,
    stage_number INT NOT NULL,
    stage_name VARCHAR(100) NOT NULL,
    percentage DECIMAL(5, 2) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    status ENUM('PENDING', 'IN_PROGRESS', 'COMPLETED') DEFAULT 'PENDING' NOT NULL,
    completed_at TIMESTAMP NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
    INDEX idx_booking_milestone (booking_id, stage_number)
);
