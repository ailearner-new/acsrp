"""Mock SendGrid email integration for testing."""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class Email:
    """Mock email record."""
    email_id: str
    to: str
    subject: str
    content: str
    from_email: str
    sent_at: str
    status: str  # 'sent', 'queued', 'failed'


class MockSendGrid:
    """Mock SendGrid API client for testing."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize mock SendGrid client."""
        self.api_key = api_key or "SG.mock_api_key"
        self.emails: List[Email] = []
        self.default_from = "support@example.com"

    async def send_email(
        self,
        to: str,
        subject: str,
        content: str,
        from_email: Optional[str] = None,
        html_content: Optional[str] = None,
        template_id: Optional[str] = None,
        dynamic_template_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send an email.

        Args:
            to: Recipient email address
            subject: Email subject
            content: Plain text content
            from_email: Sender email (optional)
            html_content: HTML content (optional)
            template_id: Template ID for SendGrid templates
            dynamic_template_data: Data for template variables

        Returns:
            Send result
        """
        email_id = str(uuid.uuid4())

        email = Email(
            email_id=email_id,
            to=to,
            subject=subject,
            content=content,
            from_email=from_email or self.default_from,
            sent_at=datetime.utcnow().isoformat() + "Z",
            status="sent",
        )
        self.emails.append(email)

        return {
            "message_id": email_id,
            "status": "success",
            "to": to,
            "subject": subject,
        }

    async def send_template(
        self,
        to: str,
        template_id: str,
        dynamic_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Send an email using a template.

        Args:
            to: Recipient email address
            template_id: SendGrid template ID
            dynamic_data: Template variable data

        Returns:
            Send result
        """
        subject = dynamic_data.get("subject", "Notification")
        content = dynamic_data.get("content", "")

        return await self.send_email(
            to=to,
            subject=subject,
            content=content,
            template_id=template_id,
        )

    async def send_bulk(
        self,
        recipients: List[str],
        subject: str,
        content: str,
        template_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send email to multiple recipients.

        Args:
            recipients: List of recipient email addresses
            subject: Email subject
            content: Email content
            template_id: Optional template ID

        Returns:
            Bulk send result
        """
        results = []
        for recipient in recipients:
            result = await self.send_email(
                to=recipient,
                subject=subject,
                content=content,
                template_id=template_id,
            )
            results.append(result)

        return {
            "status": "success",
            "total_sent": len(results),
            "recipients": recipients,
        }

    def list_emails(
        self,
        to: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List sent emails with optional filters.

        Args:
            to: Filter by recipient
            status: Filter by status
            limit: Maximum results

        Returns:
            List of email records
        """
        emails = self.emails

        if to:
            emails = [e for e in emails if e.to == to]

        if status:
            emails = [e for e in emails if e.status == status]

        return [vars(e) for e in emails[:limit]]


class MockEmailClient:
    """Higher-level email client with convenience methods."""

    def __init__(self, sendgrid: Optional[MockSendGrid] = None):
        """Initialize email client."""
        self.sendgrid = sendgrid or MockSendGrid()

    async def send_notification(
        self,
        customer_email: str,
        subject: str,
        message: str,
        customer_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a customer notification email.

        Args:
            customer_email: Customer email address
            subject: Email subject
            message: Email body
            customer_name: Customer name for personalization

        Returns:
            Send result
        """
        if customer_name:
            content = f"Hi {customer_name},\n\n{message}"
        else:
            content = message

        return await self.sendgrid.send_email(
            to=customer_email,
            subject=subject,
            content=content,
        )

    async def send_ticket_update(
        self,
        customer_email: str,
        ticket_id: str,
        update_message: str,
        status: str,
    ) -> Dict[str, Any]:
        """Send a ticket update notification.

        Args:
            customer_email: Customer email address
            ticket_id: Ticket ID
            update_message: Update message
            status: Current ticket status

        Returns:
            Send result
        """
        subject = f"Ticket #{ticket_id} - {status}"
        content = f"""
Ticket #{ticket_id}

Status: {status}

Update: {update_message}

---
CloudDesk Support
        """

        return await self.sendgrid.send_email(
            to=customer_email,
            subject=subject,
            content=content,
        )

    async def send_refund_confirmation(
        self,
        customer_email: str,
        amount: float,
        transaction_id: str,
        ticket_id: str,
    ) -> Dict[str, Any]:
        """Send a refund confirmation email.

        Args:
            customer_email: Customer email address
            amount: Refund amount
            transaction_id: Stripe transaction ID
            ticket_id: Related ticket ID

        Returns:
            Send result
        """
        subject = f"Refund Processed - ${amount:.2f}"
        content = f"""
Your refund has been processed!

Amount: ${amount:.2f}
Transaction ID: {transaction_id}
Ticket: #{ticket_id}

The refund will appear in your account within 5-10 business days.

Thank you for your patience.

Best regards,
CloudDesk Support Team
        """

        return await self.sendgrid.send_email(
            to=customer_email,
            subject=subject,
            content=content,
        )