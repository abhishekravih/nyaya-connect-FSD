-- NyayaConnect MySQL 8.0 Initial Database Schema & Seed Data
-- Person 4: System Integration & DevOps Lead
-- Mapped to: /docker-entrypoint-initdb.d/1_schema.sql

CREATE DATABASE IF NOT EXISTS nyayaconnect;
USE nyayaconnect;

-- Lawyers Directory Table
CREATE TABLE IF NOT EXISTS lawyers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    category ENUM('Consumer', 'Civil', 'Criminal') NOT NULL,
    bar_council_id VARCHAR(50) UNIQUE NOT NULL,
    experience_years INT NOT NULL DEFAULT 1,
    consultation_fee DECIMAL(10, 2) NOT NULL,
    rating DECIMAL(3, 2) DEFAULT 5.0,
    reviews_count INT DEFAULT 0,
    verified BOOLEAN DEFAULT TRUE,
    languages VARCHAR(255) DEFAULT 'English, Hindi',
    location VARCHAR(150) NOT NULL,
    milestones JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Client Bookings with 4 Smart Milestones
CREATE TABLE IF NOT EXISTS bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    lawyer_id INT NOT NULL,
    client_name VARCHAR(150) NOT NULL,
    client_phone VARCHAR(20) NOT NULL,
    case_category VARCHAR(50) NOT NULL,
    current_milestone INT DEFAULT 1,
    total_fee DECIMAL(10, 2) NOT NULL,
    payment_status ENUM('Pending', 'In_Escrow', 'Released') DEFAULT 'Pending',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lawyer_id) REFERENCES lawyers(id) ON DELETE CASCADE
);

-- Seed Data: Verified Affordable Lawyers across Consumer, Civil, and Criminal Domains
INSERT INTO lawyers (id, name, category, bar_council_id, experience_years, consultation_fee, rating, reviews_count, verified, languages, location, milestones)
VALUES
(1, 'Adv. Rajeshwari Hegde', 'Consumer', 'KAR/2014/4891', 9, 799.00, 4.9, 142, TRUE, 'Kannada, English, Hindi', 'Bengaluru, Karnataka', 
 JSON_ARRAY(
   '1. Notice Drafting & Statutory Demand',
   '2. District Consumer Commission Filing',
   '3. Evidence & Rejoinder Submission',
   '4. Final Arguments & Compensation Award'
 )),
(2, 'Adv. Karthik Sundaram', 'Consumer', 'KAR/2017/2301', 6, 950.00, 4.8, 98, TRUE, 'Kannada, Tamil, English', 'Bengaluru, Karnataka',
 JSON_ARRAY(
   '1. Case Evaluation & Evidence Review',
   '2. Legal Notice Issue',
   '3. Consumer Forum Filing',
   '4. Settlement / Order Enforcement'
 )),
(3, 'Adv. Priya Sharma', 'Consumer', 'DEL/2015/8812', 8, 1200.00, 4.7, 87, TRUE, 'Hindi, English', 'Delhi NCR / Virtual',
 JSON_ARRAY(
   '1. Consultation & Document Audit',
   '2. Legal Demand Formulation',
   '3. State Commission Briefing',
   '4. Decree Execution'
 )),
(4, 'Adv. Ramesh Babu', 'Civil', 'KAR/2009/1192', 14, 999.00, 4.9, 215, TRUE, 'Kannada, Telugu, English', 'Bengaluru, Karnataka',
 JSON_ARRAY(
   '1. Title Deed & Encumbrance Verification',
   '2. Injunction Application Drafting',
   '3. Trial Court Submissions',
   '4. Final Decree & Partition Enforcement'
 )),
(5, 'Adv. Meenakshi Venkat', 'Civil', 'TN/2012/6541', 11, 1100.00, 4.8, 134, TRUE, 'Tamil, English, Kannada', 'Chennai / Bengaluru',
 JSON_ARRAY(
   '1. Mediation & Negotiation Session',
   '2. Settlement Deed Drafting',
   '3. Civil Suit Registration',
   '4. Court Ratification'
 )),
(6, 'Adv. Farooq Ahmed', 'Criminal', 'KAR/2011/3342', 12, 1200.00, 4.9, 189, TRUE, 'Kannada, Urdu, Hindi, English', 'Bengaluru, Karnataka',
 JSON_ARRAY(
   '1. FIR Copy Analysis & Legal Strategy',
   '2. Bail / Anticipatory Bail Filing',
   '3. Sessions Court Hearing',
   '4. Trial Preparation & Quashing Petition'
 )),
(7, 'Adv. Deepa Narayan', 'Criminal', 'KAR/2018/1423', 6, 1350.00, 4.8, 91, TRUE, 'Kannada, English, Hindi', 'Bengaluru, Karnataka',
 JSON_ARRAY(
   '1. Cyber Cell Police Complaint',
   '2. Bank Account Freeze Petition',
   '3. Magistrate Hearing Representation',
   '4. Recovery / Trial Advocacy'
 ))
ON DUPLICATE KEY UPDATE name=VALUES(name);
