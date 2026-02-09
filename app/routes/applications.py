"""
SkillHive - Application Routes
================================
Handles the resource application workflow:
  1. Resource applies for a demand (uploads resume + fills form)
  2. PMO/Evaluator reviews applications
  3. Status updates: Applied → Under Evaluation → Selected / Rejected
  4. Email notifications sent at each status change
"""

import os
import uuid
from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, current_app, send_from_directory, abort
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models import Demand, Application, ApplicationHistory
from app.forms import ApplicationForm, ApplicationStatusForm
from app.utils.decorators import pmo_required, evaluator_required

applications_bp = Blueprint('applications', __name__, template_folder='templates')


# =====================================================
# APPLY FOR A DEMAND (Resource)
# =====================================================

@applications_bp.route('/apply/<int:demand_id>', methods=['GET', 'POST'])
@login_required
def apply(demand_id):
    """
    Apply for evaluation against a specific demand.
    Resources fill out a short form and upload their one-page resume.
    Sends email notification to the demand raiser and evaluator.
    """
    demand = Demand.query.get_or_404(demand_id)

    # Validate that the demand is still open
    if not demand.is_open:
        flash('This demand is no longer accepting applications.', 'warning')
        return redirect(url_for('demands.detail', demand_id=demand_id))

    # Check if user has already applied
    existing_application = Application.query.filter_by(
        demand_id=demand_id,
        user_id=current_user.id
    ).first()

    if existing_application:
        flash('You have already applied for this demand.', 'info')
        return redirect(url_for('applications.my_applications'))

    form = ApplicationForm()

    # Pre-fill form with user's info if available
    if request.method == 'GET':
        form.applicant_name.data = current_user.display_name
        form.enterprise_id.data = current_user.enterprise_id

    if form.validate_on_submit():
        try:
            # Handle resume file upload
            resume_filename = None
            resume_blob_url = None

            if form.resume.data:
                resume_filename, resume_blob_url = _handle_resume_upload(
                    form.resume.data, demand_id, current_user.id
                )

            # Create the application
            application = Application(
                demand_id=demand_id,
                user_id=current_user.id,
                applicant_name=form.applicant_name.data,
                enterprise_id=form.enterprise_id.data,
                current_project=form.current_project.data,
                years_of_experience=form.years_of_experience.data,
                skills_text=form.skills_text.data,
                resume_filename=resume_filename,
                resume_blob_url=resume_blob_url,
                status='applied'
            )
            db.session.add(application)

            # Create initial history entry
            history = ApplicationHistory(
                application=application,
                old_status=None,
                new_status='applied',
                changed_by=current_user.id,
                remarks='Application submitted'
            )
            db.session.add(history)

            # Update demand status to in_progress if it was open
            if demand.status == 'open':
                demand.status = 'in_progress'

            db.session.commit()

            # Send email notifications
            try:
                from app.services.email_service import send_application_notification
                send_application_notification(application, demand)
            except Exception as e:
                current_app.logger.warning(f"Failed to send application email: {e}")

            flash('Your application has been submitted successfully! 🎉', 'success')
            return redirect(url_for('applications.my_applications'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error submitting application: {e}")
            flash('Failed to submit application. Please try again.', 'danger')

    return render_template(
        'applications/apply.html',
        form=form,
        demand=demand
    )


# =====================================================
# MY APPLICATIONS (Resource view)
# =====================================================

@applications_bp.route('/my')
@login_required
def my_applications():
    """
    View the current user's applications and their statuses.
    Resources can track their application workflow here.
    """
    page = request.args.get('page', 1, type=int)

    applications = (
        Application.query
        .filter_by(user_id=current_user.id)
        .order_by(Application.applied_at.desc())
        .paginate(page=page, per_page=20, error_out=False)
    )

    return render_template(
        'applications/my_applications.html',
        applications=applications
    )


# =====================================================
# MANAGE APPLICATIONS (PMO / Evaluator view)
# =====================================================

@applications_bp.route('/manage')
@login_required
@evaluator_required
def manage():
    """
    Manage all applications across demands.
    PMO and evaluators can review, filter, and update application statuses.
    """
    page = request.args.get('page', 1, type=int)

    # Build query with filters
    query = Application.query.join(Demand)

    # Status filter
    status_filter = request.args.get('status', '')
    if status_filter:
        query = query.filter(Application.status == status_filter)

    # Demand filter
    demand_filter = request.args.get('demand_id', '', type=str)
    if demand_filter:
        query = query.filter(Application.demand_id == int(demand_filter))

    # Search
    search = request.args.get('search', '').strip()
    if search:
        search_pattern = f'%{search}%'
        query = query.filter(
            db.or_(
                Application.applicant_name.ilike(search_pattern),
                Application.enterprise_id.ilike(search_pattern),
                Demand.project_name.ilike(search_pattern),
            )
        )

    applications = (
        query.order_by(Application.applied_at.desc())
        .paginate(page=page, per_page=20, error_out=False)
    )

    # Get demands for filter dropdown
    demands = Demand.query.order_by(Demand.project_name).all()

    return render_template(
        'applications/manage.html',
        applications=applications,
        demands=demands,
        filters={
            'status': status_filter,
            'demand_id': demand_filter,
            'search': search,
        }
    )


# =====================================================
# UPDATE APPLICATION STATUS (PMO / Evaluator)
# =====================================================

@applications_bp.route('/<int:application_id>/status', methods=['POST'])
@login_required
@evaluator_required
def update_status(application_id):
    """
    Update the status of an application.
    Workflow: Applied → Under Evaluation → Selected / Rejected
    Sends email notification to the applicant on status change.
    """
    application = Application.query.get_or_404(application_id)
    form = ApplicationStatusForm()

    if form.validate_on_submit():
        old_status = application.status
        new_status = form.status.data
        remarks = form.remarks.data

        # Validate status transition
        valid_transitions = {
            'applied': ['under_evaluation', 'rejected'],
            'under_evaluation': ['selected', 'rejected', 'applied'],
            'selected': ['under_evaluation'],
            'rejected': ['under_evaluation', 'applied'],
        }

        if new_status not in valid_transitions.get(old_status, []) and new_status != old_status:
            flash(f'Invalid status transition from {old_status} to {new_status}.', 'danger')
            return redirect(request.referrer or url_for('applications.manage'))

        try:
            application.status = new_status
            application.remarks = remarks

            # Create history entry for audit trail
            history = ApplicationHistory(
                application_id=application_id,
                old_status=old_status,
                new_status=new_status,
                changed_by=current_user.id,
                remarks=remarks
            )
            db.session.add(history)
            db.session.commit()

            # Send email notification about status change
            try:
                from app.services.email_service import send_status_update_notification
                send_status_update_notification(application, old_status, new_status)
            except Exception as e:
                current_app.logger.warning(f"Failed to send status update email: {e}")

            flash(
                f'Application status updated: {old_status.replace("_", " ").title()} → '
                f'{new_status.replace("_", " ").title()} ✅',
                'success'
            )

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating application status: {e}")
            flash('Failed to update application status.', 'danger')

    return redirect(request.referrer or url_for('applications.manage'))


# =====================================================
# VIEW APPLICATION DETAIL
# =====================================================

@applications_bp.route('/<int:application_id>')
@login_required
def detail(application_id):
    """
    View full details of a specific application including status history.
    Accessible by the applicant, PMO, and evaluators.
    """
    application = Application.query.get_or_404(application_id)

    # Only allow the applicant, PMO, or evaluators to view
    if (application.user_id != current_user.id
            and not current_user.is_pmo
            and not current_user.is_evaluator):
        abort(403)

    # Get status history
    history = application.history.all()

    # Status update form (for PMO/evaluator)
    status_form = ApplicationStatusForm()
    status_form.status.data = application.status

    return render_template(
        'applications/detail.html',
        application=application,
        history=history,
        status_form=status_form
    )


# =====================================================
# DOWNLOAD RESUME
# =====================================================

@applications_bp.route('/<int:application_id>/resume')
@login_required
def download_resume(application_id):
    """
    Download the resume attached to an application.
    Accessible by the applicant, PMO, and evaluators.
    """
    application = Application.query.get_or_404(application_id)

    # Access control
    if (application.user_id != current_user.id
            and not current_user.is_pmo
            and not current_user.is_evaluator):
        abort(403)

    if not application.resume_filename:
        flash('No resume attached to this application.', 'warning')
        return redirect(url_for('applications.detail', application_id=application_id))

    # Check if using Azure Blob Storage or local storage
    if application.resume_blob_url and not current_app.config.get('DEV_MODE'):
        # Redirect to the blob URL (with SAS token in production)
        return redirect(application.resume_blob_url)
    else:
        # Serve from local uploads directory
        upload_dir = current_app.config.get('UPLOAD_FOLDER')
        if os.path.exists(os.path.join(upload_dir, application.resume_filename)):
            return send_from_directory(
                upload_dir,
                application.resume_filename,
                as_attachment=True,
                download_name=application.resume_filename
            )
        else:
            flash('Resume file not found.', 'danger')
            return redirect(url_for('applications.detail', application_id=application_id))


# =====================================================
# EXPORT APPLICATIONS TO EXCEL
# =====================================================

@applications_bp.route('/export')
@login_required
@evaluator_required
def export_excel():
    """Export all applications to an Excel file."""
    from app.services.export_service import export_applications_to_excel

    try:
        # Optional filter by demand
        demand_id = request.args.get('demand_id', type=int)
        return export_applications_to_excel(demand_id=demand_id)
    except Exception as e:
        current_app.logger.error(f"Error exporting applications: {e}")
        flash('Failed to export applications.', 'danger')
        return redirect(url_for('applications.manage'))


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def _handle_resume_upload(file, demand_id, user_id):
    """
    Handle resume file upload.
    In DEV_MODE: saves to local filesystem
    In Production: uploads to Azure Blob Storage

    Args:
        file: FileStorage object from the form
        demand_id: ID of the demand being applied to
        user_id: ID of the applicant

    Returns:
        Tuple of (filename, blob_url_or_none)
    """
    if not file:
        return None, None

    # Generate a unique filename to prevent collisions
    original_filename = secure_filename(file.filename)
    extension = original_filename.rsplit('.', 1)[-1].lower() if '.' in original_filename else ''

    if extension not in current_app.config.get('ALLOWED_EXTENSIONS', {'docx', 'pptx'}):
        raise ValueError(f'File type .{extension} is not allowed. Use .docx or .pptx')

    unique_filename = f"resume_{demand_id}_{user_id}_{uuid.uuid4().hex[:8]}.{extension}"

    if current_app.config.get('DEV_MODE') or not current_app.config.get('AZURE_STORAGE_CONNECTION_STRING'):
        # Local storage (development mode)
        upload_dir = current_app.config.get('UPLOAD_FOLDER')
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, unique_filename)
        file.save(file_path)
        return unique_filename, None
    else:
        # Azure Blob Storage (production)
        try:
            from azure.storage.blob import BlobServiceClient

            blob_service = BlobServiceClient.from_connection_string(
                current_app.config['AZURE_STORAGE_CONNECTION_STRING']
            )
            container_client = blob_service.get_container_client(
                current_app.config['AZURE_STORAGE_CONTAINER']
            )

            # Create container if it doesn't exist
            try:
                container_client.create_container()
            except Exception:
                pass  # Container already exists

            # Upload the file
            blob_client = container_client.get_blob_client(unique_filename)
            blob_client.upload_blob(file.read(), overwrite=True)

            blob_url = blob_client.url
            return unique_filename, blob_url

        except Exception as e:
            current_app.logger.error(f"Blob upload failed, falling back to local: {e}")
            # Fallback to local storage
            upload_dir = current_app.config.get('UPLOAD_FOLDER')
            os.makedirs(upload_dir, exist_ok=True)
            file.seek(0)  # Reset file pointer after failed upload
            file_path = os.path.join(upload_dir, unique_filename)
            file.save(file_path)
            return unique_filename, None
