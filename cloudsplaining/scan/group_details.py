"""Processes an entry under GroupDetailList"""
from cloudsplaining.scan.inline_policy import InlinePolicy
from cloudsplaining.shared.utils import is_aws_managed
from cloudsplaining.shared.exclusions import DEFAULT_EXCLUSIONS, Exclusions


class GroupDetailList:
    """Processes all entries under the GroupDetailList"""
    def __init__(self, group_details, policy_details, exclusions=DEFAULT_EXCLUSIONS):
        self.groups = []
        if not isinstance(exclusions, Exclusions):
            raise Exception(
                "The exclusions provided is not an Exclusions type object. "
                "Please supply an Exclusions object and try again."
            )
        self.exclusions = exclusions

        for group_detail in group_details:
            self.groups.append(GroupDetail(group_detail, policy_details, exclusions))

    def get_group_detail(self, name):
        """Get a GroupDetail object by providing the Name of the group. This is useful to UserDetail objects"""
        result = None
        for group_detail in self.groups:
            if group_detail.group_name == name:
                result = group_detail
                break
        return result

    def get_all_allowed_actions_for_group(self, name):
        """Returns a list of all allowed actions by the group across all its policies"""
        result = None
        for group_detail in self.groups:
            if group_detail.group_name == name:
                result = group_detail.all_allowed_actions
                break
        return result

    def get_all_iam_statements_for_group(self, name):
        """Returns a list of all StatementDetail objects across all the policies assigned to the group"""
        result = None
        for group_detail in self.groups:
            if group_detail.group_name == name:
                result = group_detail.all_iam_statements
                break
        return result

    @property
    def group_names(self):
        """Get a list of all group names in the account"""
        results = []
        for group_detail in self.groups:
            results.append(group_detail.group_name)
        results.sort()
        return results

    @property
    def inline_policies_json(self):
        """Return JSON representation of attached inline policies"""
        results = {}
        for group_detail in self.groups:
            group_inline_policies = group_detail.inline_policies_json
            if group_inline_policies:
                for k in group_inline_policies:
                    if k not in results.keys():
                        results[k] = group_inline_policies[k].copy()
        return results

    @property
    def json(self):
        """Get all JSON results"""
        result = {}
        for group in self.groups:
            result[group.group_id] = group.json
        return result


# pylint: disable=too-many-instance-attributes
class GroupDetail:
    """Processes an entry under GroupDetailList"""
    def __init__(self, group_detail, policy_details, exclusions=DEFAULT_EXCLUSIONS):
        """
        Initialize the GroupDetail object.

        :param group_detail: Details about a particular group
        :param policy_details: The ManagedPolicyDetails object - i.e., details about all managed policies in the account so the group can inherit those attributes
        """
        self.create_date = group_detail.get("CreateDate")
        self.arn = group_detail.get("Arn")
        self.path = group_detail.get("Path")
        self.group_id = group_detail.get("GroupId")
        self.group_name = group_detail.get("GroupName")

        if not isinstance(exclusions, Exclusions):
            raise Exception(
                "The exclusions provided is not an Exclusions type object. "
                "Please supply an Exclusions object and try again."
            )
        self.is_excluded = self._is_excluded(exclusions)

        # Inline Policies
        self.inline_policies = []
        if group_detail.get("GroupPolicyList"):
            self._inline_policies_details(
                group_detail.get("GroupPolicyList")
            )

        # Managed Policies (either AWS-managed or Customer managed)
        self.attached_managed_policies = []
        if group_detail.get("AttachedManagedPolicies"):
            self._attached_managed_policies_details(
                group_detail.get("AttachedManagedPolicies"),
                policy_details
            )

    def _is_excluded(self, exclusions):
        """Determine whether the principal name or principal ID is excluded"""
        return bool(
            exclusions.is_principal_excluded(self.group_name, "Group")
            or exclusions.is_principal_excluded(self.group_name, "Group")
            or exclusions.is_principal_excluded(self.path, "Group")
        )

    def _attached_managed_policies_details(self, attached_managed_policies_list, policy_details):
        for policy in attached_managed_policies_list:
            arn = policy.get("PolicyArn")
            attached_managed_policy_details = policy_details.get_policy_detail(arn)
            self.attached_managed_policies.append(attached_managed_policy_details)

    def _inline_policies_details(self, group_policies_list):
        for policy in group_policies_list:
            inline_policy = InlinePolicy(policy)
            self.inline_policies.append(inline_policy)

    @property
    def all_allowed_actions(self):
        """Return a list of which actions are allowed by the principal"""
        privileges = []
        for managed_policy in self.attached_managed_policies:
            privileges.extend(managed_policy.policy_document.all_allowed_actions)
        for inline_policy in self.inline_policies:
            privileges.extend(inline_policy.policy_document.all_allowed_actions)
        return privileges

    @property
    def all_iam_statements(self):
        """Return a list of which actions are allowed by the principal"""
        statements = []
        for managed_policy in self.attached_managed_policies:
            statements.extend(managed_policy.policy_document.statements)
        for inline_policy in self.inline_policies:
            statements.extend(inline_policy.policy_document.statements)
        return statements

    @property
    def attached_managed_policies_json(self):
        """Return JSON representation of attached managed policies"""
        policies = {}
        for policy in self.attached_managed_policies:
            policies[policy.policy_id] = policy.json_large
        return policies

    @property
    def attached_managed_policies_pointer_json(self):
        """Return metadata on attached managed policies so you can look it up in the policies section later."""
        policies = {}
        for policy in self.attached_managed_policies:
            policies[policy.policy_id] = policy.policy_name
        return policies

    @property
    def attached_customer_managed_policies_pointer_json(self):
        """Return metadata on attached managed policies so you can look it up in the policies section later."""
        policies = {}
        for policy in self.attached_managed_policies:
            if not is_aws_managed(policy.arn):
                policies[policy.policy_id] = policy.policy_name
        return policies

    @property
    def attached_aws_managed_policies_pointer_json(self):
        """Return metadata on attached managed policies so you can look it up in the policies section later."""
        policies = {}
        for policy in self.attached_managed_policies:
            if is_aws_managed(policy.arn):
                policies[policy.policy_id] = policy.policy_name
        return policies

    @property
    def inline_policies_json(self):
        """Return JSON representation of attached inline policies"""
        policies = {}
        for policy in self.inline_policies:
            policies[policy.policy_id] = policy.json_large
        return policies

    @property
    def inline_policies_pointer_json(self):
        """Return metadata on attached inline policies so you can look it up in the policies section later."""
        policies = {}
        for policy in self.inline_policies:
            policies[policy.policy_id] = policy.policy_name
        return policies

    @property
    def json(self):
        """Return the JSON representation of the Group Detail"""
        this_group_detail = dict(
            arn=self.arn,
            name=self.group_name,
            create_date=self.create_date,
            id=self.group_id,
            inline_policies=self.inline_policies_pointer_json,
            path=self.path,
            customer_managed_policies=self.attached_customer_managed_policies_pointer_json,
            aws_managed_policies=self.attached_aws_managed_policies_pointer_json,
            is_excluded=self.is_excluded
        )
        return this_group_detail
