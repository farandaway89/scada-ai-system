"""
Compliance and Audit Trail System for Industrial SCADA
Comprehensive compliance management, audit logging, and regulatory reporting
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import hmac
import threading
from pathlib import Path
import csv
import xml.etree.ElementTree as ET
from contextlib import contextmanager
import zipfile
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComplianceStandard(Enum):
    """Supported compliance standards"""
    ISO_27001 = "iso_27001"  # Information Security Management
    IEC_62443 = "iec_62443"  # Industrial Network and System Security
    NIST_CSF = "nist_csf"    # NIST Cybersecurity Framework
    ISO_27002 = "iso_27002"  # Information Security Controls
    NERC_CIP = "nerc_cip"    # Critical Infrastructure Protection
    SOX = "sox"              # Sarbanes-Oxley Act
    GDPR = "gdpr"            # General Data Protection Regulation
    HIPAA = "hipaa"          # Health Insurance Portability and Accountability Act
    FDA_21CFR11 = "fda_21cfr11"  # FDA 21 CFR Part 11

class AuditEventType(Enum):
    """Types of audit events"""
    SYSTEM_ACCESS = "system_access"
    DATA_MODIFICATION = "data_modification"
    CONFIGURATION_CHANGE = "configuration_change"
    SECURITY_EVENT = "security_event"
    ALARM_ACKNOWLEDGMENT = "alarm_acknowledgment"
    REPORT_GENERATION = "report_generation"
    USER_MANAGEMENT = "user_management"
    BACKUP_OPERATION = "backup_operation"
    SYSTEM_MAINTENANCE = "system_maintenance"
    POLICY_VIOLATION = "policy_violation"

class AuditSeverity(Enum):
    """Audit event severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    SECURITY = "security"

class ComplianceStatus(Enum):
    """Compliance check status"""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    UNDER_REVIEW = "under_review"
    NOT_APPLICABLE = "not_applicable"

@dataclass
class AuditEvent:
    """Audit event record"""
    event_id: str
    timestamp: datetime
    event_type: AuditEventType
    severity: AuditSeverity
    user_id: Optional[str]
    session_id: Optional[str]
    source_ip: Optional[str]
    resource_accessed: Optional[str]
    action_performed: str
    old_value: Optional[str]
    new_value: Optional[str]
    success: bool
    error_message: Optional[str]
    additional_data: Dict[str, Any]

@dataclass
class ComplianceRule:
    """Compliance rule definition"""
    rule_id: str
    standard: ComplianceStandard
    control_id: str
    title: str
    description: str
    requirement_text: str
    check_query: str
    automated: bool
    frequency_days: int
    criticality: str
    remediation_steps: List[str]

@dataclass
class ComplianceAssessment:
    """Compliance assessment result"""
    assessment_id: str
    rule_id: str
    timestamp: datetime
    status: ComplianceStatus
    score: float  # 0-100
    findings: List[str]
    evidence: Dict[str, Any]
    remediation_required: bool
    due_date: Optional[datetime]
    assigned_to: Optional[str]

class AuditTrailManager:
    """Manages audit trail logging and storage"""

    def __init__(self, db_path: str = "audit_trail.db"):
        self.db_path = db_path
        self.db_lock = threading.Lock()
        self._initialize_database()
        self.integrity_key = self._generate_integrity_key()

    def _initialize_database(self):
        """Initialize audit database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Audit events table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_events (
                        event_id TEXT PRIMARY KEY,
                        timestamp DATETIME NOT NULL,
                        event_type TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        user_id TEXT,
                        session_id TEXT,
                        source_ip TEXT,
                        resource_accessed TEXT,
                        action_performed TEXT NOT NULL,
                        old_value TEXT,
                        new_value TEXT,
                        success BOOLEAN NOT NULL,
                        error_message TEXT,
                        additional_data TEXT,
                        integrity_hash TEXT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Audit event integrity table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_integrity (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id TEXT NOT NULL,
                        previous_hash TEXT,
                        current_hash TEXT NOT NULL,
                        chain_position INTEGER NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (event_id) REFERENCES audit_events(event_id)
                    )
                """)

                # Create indexes for performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_events(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_events(event_type)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_severity ON audit_events(severity)")

                conn.commit()
                logger.info("Audit database initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing audit database: {e}")
            raise

    def _generate_integrity_key(self) -> bytes:
        """Generate key for audit trail integrity"""
        # In production, this should be stored securely and rotated regularly
        return b"audit_integrity_key_2024_scada_system"

    def log_audit_event(self, event: AuditEvent) -> bool:
        """Log an audit event with integrity protection"""
        try:
            with self.db_lock:
                # Calculate integrity hash
                event_data = self._serialize_event(event)
                integrity_hash = self._calculate_integrity_hash(event_data)

                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()

                    # Insert audit event
                    cursor.execute("""
                        INSERT INTO audit_events (
                            event_id, timestamp, event_type, severity, user_id,
                            session_id, source_ip, resource_accessed, action_performed,
                            old_value, new_value, success, error_message,
                            additional_data, integrity_hash
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        event.event_id, event.timestamp, event.event_type.value,
                        event.severity.value, event.user_id, event.session_id,
                        event.source_ip, event.resource_accessed, event.action_performed,
                        event.old_value, event.new_value, event.success,
                        event.error_message, json.dumps(event.additional_data),
                        integrity_hash
                    ))

                    # Update integrity chain
                    self._update_integrity_chain(cursor, event.event_id, integrity_hash)

                    conn.commit()

                logger.debug(f"Audit event logged: {event.event_id}")
                return True

        except Exception as e:
            logger.error(f"Error logging audit event: {e}")
            return False

    def _serialize_event(self, event: AuditEvent) -> str:
        """Serialize event for integrity calculation"""
        return json.dumps({
            'event_id': event.event_id,
            'timestamp': event.timestamp.isoformat(),
            'event_type': event.event_type.value,
            'user_id': event.user_id,
            'action_performed': event.action_performed,
            'old_value': event.old_value,
            'new_value': event.new_value,
            'success': event.success
        }, sort_keys=True)

    def _calculate_integrity_hash(self, event_data: str) -> str:
        """Calculate HMAC for event integrity"""
        return hmac.new(
            self.integrity_key,
            event_data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def _update_integrity_chain(self, cursor, event_id: str, current_hash: str):
        """Update integrity chain"""
        try:
            # Get the last hash in the chain
            cursor.execute("""
                SELECT current_hash FROM audit_integrity
                ORDER BY chain_position DESC LIMIT 1
            """)
            result = cursor.fetchone()
            previous_hash = result[0] if result else None

            # Get next position
            cursor.execute("SELECT COALESCE(MAX(chain_position), 0) + 1 FROM audit_integrity")
            next_position = cursor.fetchone()[0]

            # Insert new chain entry
            cursor.execute("""
                INSERT INTO audit_integrity (event_id, previous_hash, current_hash, chain_position)
                VALUES (?, ?, ?, ?)
            """, (event_id, previous_hash, current_hash, next_position))

        except Exception as e:
            logger.error(f"Error updating integrity chain: {e}")

    def verify_audit_integrity(self, start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Verify audit trail integrity"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Build query
                query = """
                    SELECT event_id, timestamp, event_type, severity, user_id,
                           session_id, source_ip, resource_accessed, action_performed,
                           old_value, new_value, success, error_message,
                           additional_data, integrity_hash
                    FROM audit_events
                """
                params = []

                if start_date and end_date:
                    query += " WHERE timestamp BETWEEN ? AND ?"
                    params = [start_date, end_date]

                query += " ORDER BY timestamp"

                cursor.execute(query, params)
                events = cursor.fetchall()

                # Verify each event
                total_events = len(events)
                verified_events = 0
                integrity_violations = []

                for event_data in events:
                    event = AuditEvent(
                        event_id=event_data[0],
                        timestamp=datetime.fromisoformat(event_data[1]),
                        event_type=AuditEventType(event_data[2]),
                        severity=AuditSeverity(event_data[3]),
                        user_id=event_data[4],
                        session_id=event_data[5],
                        source_ip=event_data[6],
                        resource_accessed=event_data[7],
                        action_performed=event_data[8],
                        old_value=event_data[9],
                        new_value=event_data[10],
                        success=bool(event_data[11]),
                        error_message=event_data[12],
                        additional_data=json.loads(event_data[13] or '{}')
                    )

                    # Verify integrity hash
                    expected_hash = self._calculate_integrity_hash(self._serialize_event(event))
                    stored_hash = event_data[14]

                    if expected_hash == stored_hash:
                        verified_events += 1
                    else:
                        integrity_violations.append({
                            'event_id': event.event_id,
                            'timestamp': event.timestamp.isoformat(),
                            'expected_hash': expected_hash,
                            'stored_hash': stored_hash
                        })

                return {
                    'total_events': total_events,
                    'verified_events': verified_events,
                    'integrity_violations': len(integrity_violations),
                    'verification_percentage': (verified_events / total_events * 100) if total_events > 0 else 100,
                    'violations': integrity_violations,
                    'verification_timestamp': datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"Error verifying audit integrity: {e}")
            return {'error': str(e)}

    def query_audit_events(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query audit events with filters"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM audit_events WHERE 1=1"
                params = []

                # Apply filters
                if 'start_date' in filters and 'end_date' in filters:
                    query += " AND timestamp BETWEEN ? AND ?"
                    params.extend([filters['start_date'], filters['end_date']])

                if 'user_id' in filters:
                    query += " AND user_id = ?"
                    params.append(filters['user_id'])

                if 'event_type' in filters:
                    query += " AND event_type = ?"
                    params.append(filters['event_type'])

                if 'severity' in filters:
                    query += " AND severity = ?"
                    params.append(filters['severity'])

                if 'success' in filters:
                    query += " AND success = ?"
                    params.append(filters['success'])

                query += " ORDER BY timestamp DESC"

                if 'limit' in filters:
                    query += " LIMIT ?"
                    params.append(filters['limit'])

                cursor.execute(query, params)
                events = cursor.fetchall()

                # Convert to dictionary format
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, event)) for event in events]

        except Exception as e:
            logger.error(f"Error querying audit events: {e}")
            return []

class ComplianceManager:
    """Manages compliance rules and assessments"""

    def __init__(self, db_path: str = "compliance.db"):
        self.db_path = db_path
        self._initialize_database()
        self.compliance_rules = {}
        self._load_default_rules()

    def _initialize_database(self):
        """Initialize compliance database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Compliance rules table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS compliance_rules (
                        rule_id TEXT PRIMARY KEY,
                        standard TEXT NOT NULL,
                        control_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        description TEXT,
                        requirement_text TEXT,
                        check_query TEXT,
                        automated BOOLEAN DEFAULT TRUE,
                        frequency_days INTEGER DEFAULT 30,
                        criticality TEXT DEFAULT 'medium',
                        remediation_steps TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Compliance assessments table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS compliance_assessments (
                        assessment_id TEXT PRIMARY KEY,
                        rule_id TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        status TEXT NOT NULL,
                        score REAL NOT NULL,
                        findings TEXT,
                        evidence TEXT,
                        remediation_required BOOLEAN DEFAULT FALSE,
                        due_date DATETIME,
                        assigned_to TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (rule_id) REFERENCES compliance_rules(rule_id)
                    )
                """)

                # Create indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_comp_standard ON compliance_rules(standard)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_assess_rule ON compliance_assessments(rule_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_assess_timestamp ON compliance_assessments(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_assess_status ON compliance_assessments(status)")

                conn.commit()
                logger.info("Compliance database initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing compliance database: {e}")
            raise

    def _load_default_rules(self):
        """Load default compliance rules"""
        default_rules = [
            ComplianceRule(
                rule_id="ISO27001_A.9.1.1",
                standard=ComplianceStandard.ISO_27001,
                control_id="A.9.1.1",
                title="Access Control Policy",
                description="Access control policy should be established, documented and reviewed",
                requirement_text="An access control policy shall be established, documented and reviewed based on business and information security requirements",
                check_query="SELECT COUNT(*) FROM system_policies WHERE policy_type='access_control' AND status='active'",
                automated=True,
                frequency_days=90,
                criticality="high",
                remediation_steps=[
                    "Create formal access control policy document",
                    "Get management approval for policy",
                    "Implement policy review schedule",
                    "Communicate policy to all users"
                ]
            ),
            ComplianceRule(
                rule_id="IEC62443_CR.1.1",
                standard=ComplianceStandard.IEC_62443,
                control_id="CR.1.1",
                title="Identification and Authentication Control",
                description="Users shall be uniquely identified and authenticated",
                requirement_text="The control system shall provide the capability to identify and authenticate all users (human users and software processes) that access the control system",
                check_query="SELECT COUNT(*) FROM users WHERE authentication_method IS NOT NULL",
                automated=True,
                frequency_days=30,
                criticality="critical",
                remediation_steps=[
                    "Implement unique user identification",
                    "Deploy strong authentication mechanisms",
                    "Configure account lockout policies",
                    "Implement session management"
                ]
            ),
            ComplianceRule(
                rule_id="NIST_CSF_PR.AC-1",
                standard=ComplianceStandard.NIST_CSF,
                control_id="PR.AC-1",
                title="Identity Management and Access Control",
                description="Identities and credentials are issued, managed, verified, revoked, and audited",
                requirement_text="Identity management processes and procedures are implemented to manage identities and credentials for authorized devices, users and processes",
                check_query="SELECT COUNT(*) FROM audit_events WHERE event_type='user_management' AND timestamp > datetime('now', '-30 days')",
                automated=True,
                frequency_days=30,
                criticality="high",
                remediation_steps=[
                    "Implement identity lifecycle management",
                    "Deploy privileged access management",
                    "Configure identity governance processes",
                    "Implement access reviews"
                ]
            )
        ]

        for rule in default_rules:
            self.add_compliance_rule(rule)

    def add_compliance_rule(self, rule: ComplianceRule) -> bool:
        """Add a new compliance rule"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT OR REPLACE INTO compliance_rules (
                        rule_id, standard, control_id, title, description,
                        requirement_text, check_query, automated, frequency_days,
                        criticality, remediation_steps
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rule.rule_id, rule.standard.value, rule.control_id,
                    rule.title, rule.description, rule.requirement_text,
                    rule.check_query, rule.automated, rule.frequency_days,
                    rule.criticality, json.dumps(rule.remediation_steps)
                ))

                conn.commit()
                self.compliance_rules[rule.rule_id] = rule
                logger.info(f"Added compliance rule: {rule.rule_id}")
                return True

        except Exception as e:
            logger.error(f"Error adding compliance rule: {e}")
            return False

    def run_compliance_assessment(self, rule_id: str, audit_db_connection: sqlite3.Connection) -> ComplianceAssessment:
        """Run compliance assessment for a specific rule"""
        try:
            if rule_id not in self.compliance_rules:
                raise ValueError(f"Compliance rule not found: {rule_id}")

            rule = self.compliance_rules[rule_id]

            # Execute compliance check query
            cursor = audit_db_connection.cursor()
            cursor.execute(rule.check_query)
            result = cursor.fetchone()

            # Analyze result and determine compliance status
            assessment = self._analyze_compliance_result(rule, result)

            # Store assessment
            self._store_assessment(assessment)

            return assessment

        except Exception as e:
            logger.error(f"Error running compliance assessment for {rule_id}: {e}")
            # Return failed assessment
            return ComplianceAssessment(
                assessment_id=f"{rule_id}_{int(datetime.now().timestamp())}",
                rule_id=rule_id,
                timestamp=datetime.now(),
                status=ComplianceStatus.UNDER_REVIEW,
                score=0.0,
                findings=[f"Assessment failed: {str(e)}"],
                evidence={},
                remediation_required=True,
                due_date=datetime.now() + timedelta(days=7),
                assigned_to="compliance_officer"
            )

    def _analyze_compliance_result(self, rule: ComplianceRule, result: Any) -> ComplianceAssessment:
        """Analyze compliance check result"""
        try:
            assessment_id = f"{rule.rule_id}_{int(datetime.now().timestamp())}"
            timestamp = datetime.now()
            findings = []
            evidence = {'query_result': str(result)}
            score = 0.0
            status = ComplianceStatus.NON_COMPLIANT
            remediation_required = True

            # Basic analysis based on result
            if result and result[0] > 0:
                score = 100.0
                status = ComplianceStatus.COMPLIANT
                remediation_required = False
                findings.append("Compliance requirement satisfied")
            else:
                score = 0.0
                status = ComplianceStatus.NON_COMPLIANT
                remediation_required = True
                findings.append("Compliance requirement not satisfied")

            # Determine due date based on criticality
            if rule.criticality == "critical":
                due_date = timestamp + timedelta(days=7)
            elif rule.criticality == "high":
                due_date = timestamp + timedelta(days=14)
            else:
                due_date = timestamp + timedelta(days=30)

            return ComplianceAssessment(
                assessment_id=assessment_id,
                rule_id=rule.rule_id,
                timestamp=timestamp,
                status=status,
                score=score,
                findings=findings,
                evidence=evidence,
                remediation_required=remediation_required,
                due_date=due_date if remediation_required else None,
                assigned_to="compliance_officer" if remediation_required else None
            )

        except Exception as e:
            logger.error(f"Error analyzing compliance result: {e}")
            raise

    def _store_assessment(self, assessment: ComplianceAssessment):
        """Store compliance assessment"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO compliance_assessments (
                        assessment_id, rule_id, timestamp, status, score,
                        findings, evidence, remediation_required, due_date, assigned_to
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    assessment.assessment_id, assessment.rule_id,
                    assessment.timestamp, assessment.status.value,
                    assessment.score, json.dumps(assessment.findings),
                    json.dumps(assessment.evidence), assessment.remediation_required,
                    assessment.due_date, assessment.assigned_to
                ))

                conn.commit()

        except Exception as e:
            logger.error(f"Error storing compliance assessment: {e}")
            raise

    def run_all_assessments(self, audit_db_connection: sqlite3.Connection) -> List[ComplianceAssessment]:
        """Run all automated compliance assessments"""
        assessments = []

        for rule_id, rule in self.compliance_rules.items():
            if rule.automated:
                try:
                    assessment = self.run_compliance_assessment(rule_id, audit_db_connection)
                    assessments.append(assessment)
                except Exception as e:
                    logger.error(f"Error running assessment for {rule_id}: {e}")

        return assessments

    def get_compliance_dashboard(self) -> Dict[str, Any]:
        """Get compliance dashboard data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Get recent assessments
                cursor.execute("""
                    SELECT status, COUNT(*) as count
                    FROM compliance_assessments
                    WHERE timestamp > datetime('now', '-30 days')
                    GROUP BY status
                """)
                status_counts = dict(cursor.fetchall())

                # Get compliance score trend
                cursor.execute("""
                    SELECT DATE(timestamp) as date, AVG(score) as avg_score
                    FROM compliance_assessments
                    WHERE timestamp > datetime('now', '-30 days')
                    GROUP BY DATE(timestamp)
                    ORDER BY date
                """)
                score_trend = cursor.fetchall()

                # Get overdue remediation items
                cursor.execute("""
                    SELECT COUNT(*) as count
                    FROM compliance_assessments
                    WHERE remediation_required = 1
                    AND due_date < datetime('now')
                    AND status != 'compliant'
                """)
                overdue_items = cursor.fetchone()[0]

                # Get critical findings
                cursor.execute("""
                    SELECT r.rule_id, r.title, a.findings, a.due_date
                    FROM compliance_assessments a
                    JOIN compliance_rules r ON a.rule_id = r.rule_id
                    WHERE a.remediation_required = 1
                    AND r.criticality = 'critical'
                    AND a.status != 'compliant'
                    ORDER BY a.due_date
                    LIMIT 10
                """)
                critical_findings = cursor.fetchall()

                return {
                    'status_summary': status_counts,
                    'overall_score': sum(status_counts.get(status.value, 0) * (100 if status == ComplianceStatus.COMPLIANT else 0)
                                       for status in ComplianceStatus) / max(sum(status_counts.values()), 1),
                    'score_trend': [{'date': row[0], 'score': row[1]} for row in score_trend],
                    'overdue_items': overdue_items,
                    'critical_findings': [
                        {
                            'rule_id': row[0],
                            'title': row[1],
                            'findings': json.loads(row[2] or '[]'),
                            'due_date': row[3]
                        } for row in critical_findings
                    ],
                    'last_updated': datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"Error getting compliance dashboard: {e}")
            return {}

class ComplianceReporter:
    """Generates compliance reports for various standards"""

    def __init__(self, audit_manager: AuditTrailManager, compliance_manager: ComplianceManager):
        self.audit_manager = audit_manager
        self.compliance_manager = compliance_manager
        self.report_templates = self._load_report_templates()

    def _load_report_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load report templates for different standards"""
        return {
            ComplianceStandard.ISO_27001.value: {
                'title': 'ISO 27001 Compliance Report',
                'sections': [
                    'Executive Summary',
                    'Scope and Objectives',
                    'Assessment Results',
                    'Non-Conformities',
                    'Recommendations',
                    'Action Plan'
                ]
            },
            ComplianceStandard.IEC_62443.value: {
                'title': 'IEC 62443 Industrial Security Compliance Report',
                'sections': [
                    'Security Level Assessment',
                    'Fundamental Requirements',
                    'System Requirements',
                    'Enhanced Requirements',
                    'Risk Analysis',
                    'Mitigation Strategies'
                ]
            },
            ComplianceStandard.NIST_CSF.value: {
                'title': 'NIST Cybersecurity Framework Assessment Report',
                'sections': [
                    'Framework Overview',
                    'Current State Assessment',
                    'Target State Definition',
                    'Gap Analysis',
                    'Implementation Roadmap',
                    'Continuous Monitoring'
                ]
            }
        }

    def generate_compliance_report(self, standard: ComplianceStandard,
                                  start_date: datetime, end_date: datetime,
                                  output_format: str = 'html') -> str:
        """Generate comprehensive compliance report"""
        try:
            # Get compliance data
            compliance_data = self._collect_compliance_data(standard, start_date, end_date)

            # Generate report based on format
            if output_format.lower() == 'html':
                return self._generate_html_compliance_report(standard, compliance_data)
            elif output_format.lower() == 'xml':
                return self._generate_xml_compliance_report(standard, compliance_data)
            elif output_format.lower() == 'json':
                return self._generate_json_compliance_report(standard, compliance_data)
            else:
                raise ValueError(f"Unsupported output format: {output_format}")

        except Exception as e:
            logger.error(f"Error generating compliance report: {e}")
            raise

    def _collect_compliance_data(self, standard: ComplianceStandard,
                                start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Collect compliance data for report"""
        try:
            # Get assessments for the standard
            with sqlite3.connect(self.compliance_manager.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT a.*, r.title, r.control_id, r.criticality, r.remediation_steps
                    FROM compliance_assessments a
                    JOIN compliance_rules r ON a.rule_id = r.rule_id
                    WHERE r.standard = ? AND a.timestamp BETWEEN ? AND ?
                    ORDER BY a.timestamp DESC
                """, (standard.value, start_date, end_date))

                assessments = cursor.fetchall()

            # Get relevant audit events
            audit_events = self.audit_manager.query_audit_events({
                'start_date': start_date,
                'end_date': end_date,
                'event_type': AuditEventType.SECURITY_EVENT.value
            })

            # Calculate compliance metrics
            metrics = self._calculate_compliance_metrics(assessments)

            return {
                'standard': standard.value,
                'period': {'start': start_date, 'end': end_date},
                'assessments': assessments,
                'audit_events': audit_events,
                'metrics': metrics,
                'generated_at': datetime.now()
            }

        except Exception as e:
            logger.error(f"Error collecting compliance data: {e}")
            return {}

    def _calculate_compliance_metrics(self, assessments: List) -> Dict[str, Any]:
        """Calculate compliance metrics"""
        if not assessments:
            return {}

        total_assessments = len(assessments)
        compliant_count = len([a for a in assessments if a[4] == ComplianceStatus.COMPLIANT.value])
        non_compliant_count = len([a for a in assessments if a[4] == ComplianceStatus.NON_COMPLIANT.value])

        avg_score = sum(a[5] for a in assessments) / total_assessments if total_assessments > 0 else 0

        critical_findings = len([a for a in assessments
                               if a[4] == ComplianceStatus.NON_COMPLIANT.value and 'critical' in str(a)])

        return {
            'total_assessments': total_assessments,
            'compliant_percentage': (compliant_count / total_assessments * 100) if total_assessments > 0 else 0,
            'non_compliant_count': non_compliant_count,
            'average_score': avg_score,
            'critical_findings': critical_findings
        }

    def _generate_html_compliance_report(self, standard: ComplianceStandard,
                                       data: Dict[str, Any]) -> str:
        """Generate HTML compliance report"""
        template = self.report_templates.get(standard.value, {})

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{template.get('title', 'Compliance Report')}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .section {{ margin: 30px 0; }}
                .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }}
                .metric-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
                .metric-value {{ font-size: 2em; font-weight: bold; color: #007bff; }}
                .table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .table th, .table td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                .table th {{ background: #007bff; color: white; }}
                .status-compliant {{ color: green; font-weight: bold; }}
                .status-non-compliant {{ color: red; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{template.get('title', 'Compliance Report')}</h1>
                <p>Period: {data['period']['start']} to {data['period']['end']}</p>
                <p>Generated: {data['generated_at']}</p>
            </div>

            <div class="section">
                <h2>Compliance Metrics</h2>
                <div class="metrics">
                    <div class="metric-card">
                        <div class="metric-value">{data['metrics'].get('total_assessments', 0)}</div>
                        <div>Total Assessments</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{data['metrics'].get('compliant_percentage', 0):.1f}%</div>
                        <div>Compliance Rate</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{data['metrics'].get('average_score', 0):.1f}</div>
                        <div>Average Score</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{data['metrics'].get('critical_findings', 0)}</div>
                        <div>Critical Findings</div>
                    </div>
                </div>
            </div>

            <div class="section">
                <h2>Assessment Details</h2>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Control ID</th>
                            <th>Title</th>
                            <th>Status</th>
                            <th>Score</th>
                            <th>Date</th>
                            <th>Criticality</th>
                        </tr>
                    </thead>
                    <tbody>
        """

        # Add assessment rows
        for assessment in data.get('assessments', []):
            status_class = 'status-compliant' if assessment[4] == 'compliant' else 'status-non-compliant'
            html_content += f"""
                        <tr>
                            <td>{assessment[10]}</td>  <!-- control_id -->
                            <td>{assessment[9]}</td>   <!-- title -->
                            <td class="{status_class}">{assessment[4].upper()}</td>  <!-- status -->
                            <td>{assessment[5]:.1f}</td>  <!-- score -->
                            <td>{assessment[3]}</td>   <!-- timestamp -->
                            <td>{assessment[11]}</td>  <!-- criticality -->
                        </tr>
            """

        html_content += """
                    </tbody>
                </table>
            </div>
        </body>
        </html>
        """

        # Save report
        report_path = Path(f"compliance_report_{standard.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return str(report_path)

    def _generate_xml_compliance_report(self, standard: ComplianceStandard,
                                      data: Dict[str, Any]) -> str:
        """Generate XML compliance report"""
        # Create XML structure
        root = ET.Element("ComplianceReport")

        # Header
        header = ET.SubElement(root, "Header")
        ET.SubElement(header, "Standard").text = standard.value
        ET.SubElement(header, "StartDate").text = data['period']['start'].isoformat()
        ET.SubElement(header, "EndDate").text = data['period']['end'].isoformat()
        ET.SubElement(header, "GeneratedAt").text = data['generated_at'].isoformat()

        # Metrics
        metrics = ET.SubElement(root, "Metrics")
        for key, value in data['metrics'].items():
            ET.SubElement(metrics, key.replace('_', '')).text = str(value)

        # Assessments
        assessments = ET.SubElement(root, "Assessments")
        for assessment in data.get('assessments', []):
            assess_elem = ET.SubElement(assessments, "Assessment")
            ET.SubElement(assess_elem, "AssessmentId").text = assessment[0]
            ET.SubElement(assess_elem, "RuleId").text = assessment[1]
            ET.SubElement(assess_elem, "Timestamp").text = assessment[2]
            ET.SubElement(assess_elem, "Status").text = assessment[4]
            ET.SubElement(assess_elem, "Score").text = str(assessment[5])

        # Save XML report
        report_path = Path(f"compliance_report_{standard.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml")
        tree = ET.ElementTree(root)
        tree.write(report_path, encoding='utf-8', xml_declaration=True)

        return str(report_path)

    def _generate_json_compliance_report(self, standard: ComplianceStandard,
                                       data: Dict[str, Any]) -> str:
        """Generate JSON compliance report"""
        # Convert data to JSON-serializable format
        json_data = {
            'header': {
                'standard': standard.value,
                'start_date': data['period']['start'].isoformat(),
                'end_date': data['period']['end'].isoformat(),
                'generated_at': data['generated_at'].isoformat()
            },
            'metrics': data['metrics'],
            'assessments': [
                {
                    'assessment_id': assessment[0],
                    'rule_id': assessment[1],
                    'timestamp': assessment[2],
                    'status': assessment[4],
                    'score': assessment[5],
                    'title': assessment[9],
                    'control_id': assessment[10],
                    'criticality': assessment[11]
                } for assessment in data.get('assessments', [])
            ],
            'audit_events_count': len(data.get('audit_events', []))
        }

        # Save JSON report
        report_path = Path(f"compliance_report_{standard.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, default=str)

        return str(report_path)

# Example usage and testing
if __name__ == "__main__":
    # Initialize audit trail manager
    audit_manager = AuditTrailManager()

    # Initialize compliance manager
    compliance_manager = ComplianceManager()

    # Log sample audit events
    sample_events = [
        AuditEvent(
            event_id="evt_001",
            timestamp=datetime.now(),
            event_type=AuditEventType.SYSTEM_ACCESS,
            severity=AuditSeverity.INFO,
            user_id="admin",
            session_id="sess_001",
            source_ip="192.168.1.100",
            resource_accessed="/admin/dashboard",
            action_performed="login",
            old_value=None,
            new_value=None,
            success=True,
            error_message=None,
            additional_data={"browser": "Chrome", "os": "Windows"}
        ),
        AuditEvent(
            event_id="evt_002",
            timestamp=datetime.now(),
            event_type=AuditEventType.CONFIGURATION_CHANGE,
            severity=AuditSeverity.WARNING,
            user_id="operator",
            session_id="sess_002",
            source_ip="192.168.1.101",
            resource_accessed="/config/alarms",
            action_performed="modify_alarm_threshold",
            old_value="80",
            new_value="85",
            success=True,
            error_message=None,
            additional_data={"alarm_tag": "TEMP_001"}
        )
    ]

    for event in sample_events:
        audit_manager.log_audit_event(event)

    # Run compliance assessments
    audit_db_conn = sqlite3.connect(audit_manager.db_path)
    assessments = compliance_manager.run_all_assessments(audit_db_conn)

    print(f"Completed {len(assessments)} compliance assessments")

    # Verify audit integrity
    integrity_result = audit_manager.verify_audit_integrity()
    print(f"Audit integrity verification: {integrity_result['verification_percentage']:.1f}% verified")

    # Generate compliance report
    reporter = ComplianceReporter(audit_manager, compliance_manager)

    report_path = reporter.generate_compliance_report(
        ComplianceStandard.ISO_27001,
        datetime.now() - timedelta(days=30),
        datetime.now(),
        'html'
    )

    print(f"Compliance report generated: {report_path}")

    # Get compliance dashboard
    dashboard = compliance_manager.get_compliance_dashboard()
    print(f"Compliance dashboard: {json.dumps(dashboard, indent=2, default=str)}")

    audit_db_conn.close()