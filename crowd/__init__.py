from django import forms
from djblets.siteconfig.forms import SiteSettingsForm
from djblets.siteconfig.models import SiteConfiguration
from reviewboard.accounts.backends import AuthBackend
from django.contrib.auth.models import User
from reviewboard.reviews.models import Group
import requests
import json
import logging
import traceback

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

        # Add the user to whatever groups they can belong.
        # This keeps them from seeing a blank screen when
        # they first log in
        for group in Group.objects.accessible(user):
            group.users.add(user)

        logging.debug("Created user %s" % username)

        return user

    def authenticate(self, username, password):
        username = username.strip()
        url = "%s/%s" % (auth_crowd_url.rstrip("/").strip(), "rest/usermanagement/1/authentication")
        logging.debug("Authenticating user %s" % username)
        try:
            response = requests.post(url,
                                     data=json.dumps({"value": password}),
                                     params={"username": username},
                                     auth=(auth_crowd_app, auth_crowd_pass),
                                     headers={'Content-Type': 'application/json',
                                              'Accept': 'application/json'})
        except:
            logging.error("Exception occurred while authenticating user %s" % username)
            logging.error(traceback.format_exc())
            return None

        logging.debug("Authentication returned %s" % str(response.status_code))

        # Authentication has failed
        if not response.ok:
            return None

        # To reduce HTTP calls we use the information returned to construct the user instead of
        # querying Crowd again through the get_or_create_user function
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return self.details_to_user(username, json.loads(response.content))

    def get_or_create_user(self, username):
        username = username.strip()

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            url = "%s/%s" % (auth_crowd_url.rstrip("/").strip(), "rest/usermanagement/1/user")
            logging.debug("Querying crowd for user %s" % username)
            response = requests.get(url,
                                    params={"username": username},
                                    auth=(auth_crowd_app, auth_crowd_pass),
                                    headers={'Content-Type': 'application/json',
                                             'Accept': 'application/json'})
            logging.debug("User identification returned %s" % str(response.status_code))
            if response.ok:
                return self.details_to_user(username, json.loads(response.content))
            
        return user

