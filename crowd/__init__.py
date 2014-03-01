from django import forms
from djblets.siteconfig.forms import SiteSettingsForm
from djblets.siteconfig.models import SiteConfiguration
from reviewboard.accounts.backends import AuthBackend
from django.contrib.auth.models import User
import requests
import json

siteconfig = SiteConfiguration.objects.get_current()

auth_crowd_url = siteconfig.get("auth_crowd_url")
auth_crowd_app = siteconfig.get("auth_crowd_app")
auth_crowd_pass = siteconfig.get("auth_crowd_pass")

class CrowdSettingsForm(SiteSettingsForm):
    auth_crowd_url = forms.CharField(
        label="Crowd URL",
        help_text="The URL to the Crowd instance",
        required=True,
        widget=forms.TextInput(attrs={'size': '40'}))

    auth_crowd_app = forms.CharField(
        label="Application Name",
        help_text="Application name as configured in Crowd",
        required=True,
        widget=forms.TextInput(attrs={'size': '40'}))

    auth_crowd_pass = forms.CharField(
        label="Application Password",
        help_text='Application password for authentication',
        required=True,
        widget=forms.PasswordInput(attrs={'size': '40'}))

    class Meta:
        title = "Crowd Backend Settings"

class CrowdAuthBackend(AuthBackend):
    name = "Crowd"
    settings_form = CrowdSettingsForm
    supports_registration = False
    supports_change_name = False
    supports_change_email = False
    supports_change_password = False

    def details_to_user(self, username, details):
        user = User(username=username,
                    password='',
                    first_name=details['first-name'],
                    last_name=details['last-name'],
                    email=details['email'])
        user.is_staff = False
        user.is_superuser = False
        user.set_unusable_password()
        user.save()

        return user

    def authenticate(self, username, password):
        response = requests.post(auth_crowd_url.rstrip("/") + "/rest/usermanagement/1/authentication",
                                 data=json.dumps({"value": password}),
                                 params={"username": username},
                                 auth=(auth_crowd_app, auth_crowd_pass),
                                 headers={'Content-Type': 'application/json',
                                          'Accept': 'application/json'})

        # Authentication has failed
        if not response.ok:
            return None

        # To reduce HTTP calls we use the information returned to construct the user instead of
        # querying Crowd again through the get_or_create_user function
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return self.details_to_user(username, json.loads(response.text))

    def get_or_create_user(self, username):
        username = username.strip()

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            response = requests.get(auth_crowd_url.rstrip("/") + "/rest/usermanagement/1/user",
                                     params={"username": username},
                                     auth=(auth_crowd_app, auth_crowd_pass),
                                     headers={'Content-Type': 'application/json',
                                              'Accept': 'application/json'})
            if response.ok:
                return self.details_to_user(username, json.loads(response.text))
            
        return None

