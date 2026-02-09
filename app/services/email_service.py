"""
SkillHive - Email Notification Service
========================================
Sends email notifications using Flask-Mail (SMTP).
Configured for Office 365 but works with any SMTP server.

Notifications are sent for:
  1. New demand created → demand raiser confirmation
  2. New application submitted → demand raiser + evaluator
  3. Application status updated → applicant
"""

from flask import current_app, render_template_string
from flask_mail import Message
from app import mail


# =====================================================
# EMAIL TEMPLATES (inline for simplicity)
# =====================================================

DEMAND_CREATED_TEMPLATE = """
<div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: linear-gradient(135deg, #A100FF 0%, #7B00E0 100%); padding: 30px; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 24px;">🐝 SkillHive</h1>
        <p style="color: rgba(255,255,255,0.9); margin: 5px 0 0;">DU Demand & Supply Portal</p>
    </div>
    <div style="padding: 30px; background: #f8f9fa; border: 1px solid #e9ecef;">
        <h2 style="color: #1a002e; margin-top: 0;">New Demand Created ✅</h2>
        <p>A new demand has been created in SkillHive:</p>
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr><td style="padding: 8px; font-weight: bold; color: #666;">Project:</td>
                <td style="padding: 8px;">{{ demand.project_name }}</td></tr>
            <tr style="background: #fff;"><td style="padding: 8px; font-weight: bold; color: #666;">DU:</td>
                <td style="padding: 8px;">{{ demand.du_name }}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold; color: #666;">Career Level:</td>
                <td style="padding: 8px;">CL{{ demand.career_level }}</td></tr>
            <tr style="background: #fff;"><td style="padding: 8px; font-weight: bold; color: #666;">Skills:</td>
                <td style="padding: 8px;">{{ demand.skills_display }}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold; color: #666;">Priority:</td>
                <td style="padding: 8px;">{{ demand.priority | upper }}</td></tr>
            <tr style="background: #fff;"><td style="padding: 8px; font-weight: bold; color: #666;">Positions:</td>
                <td style="padding: 8px;">{{ demand.num_positions }}</td></tr>
        </table>
        <p style="color: #666; font-size: 14px;">This is an automated notification from SkillHive portal.</p>
    </div>
</div>
"""

APPLICATION_RECEIVED_TEMPLATE = """
<div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: linear-gradient(135deg, #A100FF 0%, #7B00E0 100%); padding: 30px; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 24px;">🐝 SkillHive</h1>
        <p style="color: rgba(255,255,255,0.9); margin: 5px 0 0;">DU Demand & Supply Portal</p>
    </div>
    <div style="padding: 30px; background: #f8f9fa; border: 1px solid #e9ecef;">
        <h2 style="color: #1a002e; margin-top: 0;">New Application Received 📋</h2>
        <p>A resource has applied for evaluation:</p>
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr><td style="padding: 8px; font-weight: bold; color: #666;">Applicant:</td>
                <td style="padding: 8px;">{{ application.applicant_name }}</td></tr>
            <tr style="background: #fff;"><td style="padding: 8px; font-weight: bold; color: #666;">Enterprise ID:</td>
                <td style="padding: 8px;">{{ application.enterprise_id }}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold; color: #666;">Project:</td>
                <td style="padding: 8px;">{{ demand.project_name }}</td></tr>
            <tr style="background: #fff;"><td style="padding: 8px; font-weight: bold; color: #666;">Experience:</td>
                <td style="padding: 8px;">{{ application.years_of_experience }} years</td></tr>
            <tr><td style="padding: 8px; font-weight: bold; color: #666;">Skills:</td>
                <td style="padding: 8px;">{{ application.skills_text }}</td></tr>
            <tr style="background: #fff;"><td style="padding: 8px; font-weight: bold; color: #666;">Resume:</td>
                <td style="padding: 8px;">{{ 'Attached' if application.resume_filename else 'Not attached' }}</td></tr>
        </table>
        <p><strong>Please review this application in the SkillHive portal.</strong></p>
        <p style="color: #666; font-size: 14px;">This is an automated notification from SkillHive portal.</p>
    </div>
</div>
"""

STATUS_UPDATE_TEMPLATE = """
<div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: linear-gradient(135deg, #A100FF 0%, #7B00E0 100%); padding: 30px; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 24px;">🐝 SkillHive</h1>
        <p style="color: rgba(255,255,255,0.9); margin: 5px 0 0;">DU Demand & Supply Portal</p>
    </div>
    <div style="padding: 30px; background: #f8f9fa; border: 1px solid #e9ecef;">
        <h2 style="color: #1a002e; margin-top: 0;">Application Status Update</h2>
        <p>Your application status has been updated:</p>
        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
            <tr><td style="padding: 8px; font-weight: bold; color: #666;">Project:</td>
                <td style="padding: 8px;">{{ application.demand.project_name }}</td></tr>
            <tr style="background: #fff;"><td style="padding: 8px; font-weight: bold; color: #666;">Previous Status:</td>
                <td style="padding: 8px;">{{ old_status | replace('_', ' ') | title }}</td></tr>
            <tr><td style="padding: 8px; font-weight: bold; color: #666;">New Status:</td>
                <td style="padding: 8px; font-weight: bold; color: {{ '#28a745' if new_status == 'selected' else '#dc3545' if new_status == 'rejected' else '#ffc107' }};">
                    {{ new_status | replace('_', ' ') | title }}</td></tr>
        </table>
        {% if application.remarks %}
        <div style="background: #fff; padding: 15px; border-left: 4px solid #A100FF; margin: 15px 0;">
            <strong>Remarks:</strong><br>{{ application.remarks }}
        </div>
        {% endif %}
        <p style="color: #666; font-size: 14px;">This is an automated notification from SkillHive portal.</p>
    </div>
</div>
"""


# =====================================================
# NOTIFICATION FUNCTIONS
# =====================================================

def send_demand_notification(demand, action='created'):
    """
    Send email notification when a demand is created or updated.
    Notifies the demand raiser (creator).

    Args:
        demand: Demand model instance
        action: 'created' or 'updated'
    """
    if not _is_email_configured():
        current_app.logger.warning("Email not configured. Skipping demand notification.")
        return

    try:
        # Send to the demand creator
        creator = demand.creator
        if not creator or not creator.email:
            return

        subject = f"[SkillHive] Demand {action.title()}: {demand.project_name}"

        html_body = render_template_string(
            DEMAND_CREATED_TEMPLATE,
            demand=demand,
            action=action
        )

        msg = Message(
            subject=subject,
            recipients=[creator.email],
            html=html_body
        )

        # Also CC the evaluator if email is provided
        if demand.evaluator_email:
            msg.cc = [demand.evaluator_email]

        mail.send(msg)
        current_app.logger.info(f"Demand notification sent to {creator.email}")

    except Exception as e:
        current_app.logger.error(f"Failed to send demand notification: {e}")
        raise


def send_application_notification(application, demand):
    """
    Send email notification when a resource applies for a demand.
    Notifies:
      1. The demand raiser (person who created the demand)
      2. The evaluator (specified in the demand)

    Args:
        application: Application model instance
        demand: Demand model instance
    """
    if not _is_email_configured():
        current_app.logger.warning("Email not configured. Skipping application notification.")
        return

    try:
        recipients = []

        # Add demand creator's email
        if demand.creator and demand.creator.email:
            recipients.append(demand.creator.email)

        # Add evaluator's email
        if demand.evaluator_email and demand.evaluator_email not in recipients:
            recipients.append(demand.evaluator_email)

        if not recipients:
            current_app.logger.warning("No recipients for application notification.")
            return

        subject = (
            f"[SkillHive] New Application: {application.applicant_name} "
            f"for {demand.project_name}"
        )

        html_body = render_template_string(
            APPLICATION_RECEIVED_TEMPLATE,
            application=application,
            demand=demand
        )

        msg = Message(
            subject=subject,
            recipients=recipients,
            html=html_body
        )

        mail.send(msg)
        current_app.logger.info(
            f"Application notification sent to {', '.join(recipients)}"
        )

    except Exception as e:
        current_app.logger.error(f"Failed to send application notification: {e}")
        raise


def send_status_update_notification(application, old_status, new_status):
    """
    Send email notification when an application status changes.
    Notifies the applicant about their application status update.

    Args:
        application: Application model instance
        old_status: Previous status string
        new_status: New status string
    """
    if not _is_email_configured():
        current_app.logger.warning("Email not configured. Skipping status notification.")
        return

    try:
        # Get the applicant's email from the associated user
        applicant = application.applicant
        if not applicant or not applicant.email:
            current_app.logger.warning("Applicant email not found.")
            return

        status_emoji = {
            'under_evaluation': '🔍',
            'selected': '🎉',
            'rejected': '😔'
        }

        subject = (
            f"[SkillHive] {status_emoji.get(new_status, '📋')} Application Update: "
            f"{new_status.replace('_', ' ').title()} - {application.demand.project_name}"
        )

        html_body = render_template_string(
            STATUS_UPDATE_TEMPLATE,
            application=application,
            old_status=old_status,
            new_status=new_status
        )

        msg = Message(
            subject=subject,
            recipients=[applicant.email],
            html=html_body
        )

        mail.send(msg)
        current_app.logger.info(
            f"Status update notification sent to {applicant.email}"
        )

    except Exception as e:
        current_app.logger.error(f"Failed to send status update notification: {e}")
        raise


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def _is_email_configured():
    """Check if email credentials are properly configured."""
    return bool(
        current_app.config.get('MAIL_USERNAME')
        and current_app.config.get('MAIL_PASSWORD')
        and current_app.config.get('MAIL_SERVER')
    )
