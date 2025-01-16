# python 
import uuid

# django
from django.db import models
from django.utils.translation import gettext_lazy as _


class AccountBrowsers(models.Model):
    """
    Model to store details about devices (browsers) associated with a user's account.
    This includes device metadata, browser details, and fields for WebAuthn support.
    """

    # Relationships
    account = models.ForeignKey(
        'accounts.BaseAccount',
        on_delete=models.CASCADE,
        help_text="The account associated with this browser or device."
    )
    access_token = models.ForeignKey(
        'account_access_tokens.AccountAccessToken',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="The access token associated with this browser or device."
    )

    # Device Information
    device_type = models.CharField(
        max_length=50,
        help_text="The type of device (e.g., 'mobile', 'desktop', 'tablet')."
    )

    os = models.CharField(
        max_length=50,
        help_text="The operating system running on the device (e.g., 'Windows', 'Android', 'iOS')."
    )
    os_version = models.CharField(
        max_length=50,
        help_text="The version of the operating system (e.g., '11', '10.15.7')."
    )

    # Browser Information
    browser = models.CharField(
        max_length=50,
        help_text="The browser used on the device (e.g., 'Chrome', 'Safari', 'Firefox')."
    )
    browser_version = models.CharField(
        max_length=50,
        help_text="The version of the browser (e.g., '96.0', '14.1.2')."
    )

    # Locale and Timezone
    language = models.CharField(
        max_length=50,
        help_text="The preferred language of the device or browser (e.g., 'en-US')."
    )
    time_zone = models.CharField(
        max_length=50,
        help_text="The timezone of the device (e.g., 'UTC', 'America/New_York')."
    )

    # Timestamps
    last_used = models.DateTimeField(
        auto_now=True,
        help_text="The last time this device/browser was used for account interaction."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="The date and time this device/browser was first registered."
    )

    # Prompting for WebAuthn
    prompted = models.BooleanField(
        _('Was user prompted to register browser for WebAuthn'),
        default=False,
        help_text="Tracks whether the user was prompted to register this browser for WebAuthn but dismissed the prompt."
    )

    # static key 
    static_key = models.BinaryField(
        _('Browser Static Key'),
        blank=True,
        null=True,
        help_text="The Static key associated with this browser/device."
    )

    # WebAuthn Credentials
    registered = models.BooleanField(
        _('Is browser registered for WebAuthn'),
        default=False,
        help_text="Indicates whether this browser/device has been registered for WebAuthn."
    )
    public_key = models.BinaryField(
        _('Browser WebAuthn Public Key'),
        blank=True,
        null=True,
        help_text="The WebAuthn public key associated with this browser/device."
    )
    credential_id = models.BinaryField(
        _('WebAuthn Credential ID'),
        blank=True,
        null=True,
        help_text="The unique identifier for the WebAuthn credential (binary data)."
    )
    counter = models.PositiveIntegerField(
        _('WebAuthn Signature Counter'),
        default=0,
        help_text="Tracks the number of times this WebAuthn credential has been used to prevent replay attacks."
    )
    attestation_type = models.CharField(
        _('WebAuthn Attestation Type'),
        max_length=50,
        blank=True,
        null=True,
        help_text="The attestation type used during WebAuthn registration (e.g., 'direct', 'indirect', or 'none')."
    )
    aaguid = models.UUIDField(
        _('Authenticator AAGUID'),
        blank=True,
        null=True,
        help_text="The Authenticator Attestation GUID (AAGUID) identifying the type of authenticator."
    )
    rp_id = models.CharField(
        _('Relying Party ID'),
        max_length=255,
        blank=True,
        null=True,
        help_text="The relying party ID, typically the domain of your application."
    )
    transport = models.CharField(
        _('Authenticator Transport'),
        max_length=255,
        blank=True,
        null=True,
        help_text="The transport method(s) supported by the authenticator (e.g., 'usb', 'nfc', 'ble', 'internal')."
    )

    # Unique Browser Identifier
    browser_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        help_text="A unique identifier for this browser/device, generated as a UUID."
    )

    def __str__(self):
        """
        String representation of the model instance.
        """
        return f"{self.account.surname} - {self.device_type} - {self.os} ({self.os_version})"

