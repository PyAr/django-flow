from collections import namedtuple

from django.contrib.auth.models import User
from django.db.models import (
    BooleanField,
    CASCADE,
    CharField,
    DateTimeField,
    DecimalField,
    ForeignKey,
    ImageField,
    ManyToManyField,
    Model,
    OneToOneField,
    TextField,
)


ORGZER = 'organizer'
ADMIN = 'admin'

Step = namedtuple('Step', "index current_state role next_state fields")


class Profile(Model):
    user = OneToOneField(User, on_delete=CASCADE)
    security_clearance = CharField(max_length=256, choices=(
        (ORGZER, "Organizer"),
        (ADMIN, "Administrator"),
    ))


class Organizer(Profile):
    bank_account_info = CharField(max_length=256)
    # FIXME: complete with other organizer fields


class Event(Model):
    """All event stuff."""
    name = CharField(max_length=256)


class Sponsor(Model):
    """All sponsor stuff."""
    name = CharField(max_length=256)


class Category(Model):
    """Categories info (name, amount), related to Event."""
    name = CharField(max_length=256)
    amount = DecimalField(max_digits=20, decimal_places=2)
    event = ForeignKey(Event, on_delete=CASCADE)


class ExtraDocument(Model):
    """Extra documents for the Income."""
    image = ImageField()
    comment = TextField()


class PaymentReceived(Model):
    timestamp = DateTimeField()
    amount = DecimalField(max_digits=20, decimal_places=2)
    income = ForeignKey('Income', related_name="payments_received", on_delete=CASCADE)


def Optional(field):
    field._fsm_optional = True
    return field


class Invoice(Model):
    """Invoices info."""
    __always_new__ = True

    date = DateTimeField()
    kind = CharField(max_length=256, choices=(
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
    ))
    amount = DecimalField(max_digits=20, decimal_places=2)
    image = ImageField()


class FSMModel(Model):

    @classmethod
    def get_step_by_index(cls, index):
        step = cls.fsm[index]
        return Step(
            index=index, current_state=step[0], role=step[1], next_state=step[2], fields=step[3])

    @classmethod
    def get_steps(cls, state, role):
        steps = []
        for index, step in enumerate(cls.fsm):
            if step[0] == state and step[1] == role:
                steps.append(Step(
                    index=index, current_state=step[0],
                    role=step[1], next_state=step[2], fields=step[3]))
        return steps

    @classmethod
    def get_create_roles(cls):
        # FIXME: validate "None not found"
        roles = []
        for step in cls.fsm:
            if step[0] is None:
                roles.append(step[1])
        return roles

    def get_current_steps(self, role):
        return self.get_steps(self.state, role)


class Income(FSMModel):
    """An income of money to a given event."""

    # state related fields
    S_INIT = 'init'
    S_HAVE_INVOICE = 'have-invoice'
    S_READY_TO_PAYMENT = 'ready-to-payment'
    S_PAYMENT_DONE = 'payment-done'
    S_PARTIAL_PAYMENT = 'partial-payment'
    STATE_CHOICES = (
        (S_INIT, "Init"),
        (S_HAVE_INVOICE, "Have an invoice"),
        (S_READY_TO_PAYMENT, "Ready to payment"),
        (S_PAYMENT_DONE, "The payment is done, all finished"),
        (S_PARTIAL_PAYMENT, "Partial payment received, need more"),
    )
    state = CharField(max_length=256, choices=STATE_CHOICES)

    # fields with data
    event = ForeignKey(Event, on_delete=CASCADE)  # FIXME: limit to: Organizer
    sponsor = ForeignKey(Sponsor, on_delete=CASCADE)
    category = ForeignKey(Category, on_delete=CASCADE)
    invoice = OneToOneField(Invoice, on_delete=CASCADE, null=True)
    ready_to_payment = BooleanField(null=True)
    payment_done = BooleanField(null=True)
    # payments_received = ManyToManyField(PaymentDone)
    extra_docs = ManyToManyField(ExtraDocument)  # really OneToMany, but this will do

    @property
    def total_payments(self):
        return sum(p.amount for p in self.payments_received)

    # fsm is a state machine, each node has:
    # - the current state (None is special, it's "non created", have all the info
    #   for the first creation of the instance)
    # - who needs to work on this state (do something so the flow can progress)
    # - the next state after all info is supplied (None is special: means "done", "closed")
    # - all the fields that the user can work/change/use in that state
    fsm = [
        (None, ORGZER, S_INIT, ['event', 'sponsor', 'category']),
        (S_INIT, ADMIN, S_HAVE_INVOICE, ['invoice']),
        (S_HAVE_INVOICE, ORGZER, S_READY_TO_PAYMENT, ['ready_to_payment']),
        (S_READY_TO_PAYMENT, ADMIN, S_PAYMENT_DONE, ['payment_done']),
        (S_READY_TO_PAYMENT, ADMIN, S_PARTIAL_PAYMENT, ['payments_received']),
        (S_PARTIAL_PAYMENT, ORGZER, S_READY_TO_PAYMENT, ['extra_docs']),  # FIXME: optional!
    ]
    fsm_final_state = S_PAYMENT_DONE


# How it works / extra considerations:
# - on each state, it's presented to the user:
#     - all the instance info so far (everything that is already not null)
#     - for each possible outcome:
#         - the fields that can be operated in that step (are all mandatory???)
#         - a button to go to the next step
#     - a link to all the instance history
# - everytime the system changes state:
#     - a mail is sent to organizers/admins
#     - a record is created in the History (not with all the data, just timestamp, user,
#       Model pk), even for creation
# - the admin/organizer respective homepages will show all flows that are in a state which
#   admin/organizer is responsible
# - the admin always can go to the flow itself (through the event, for example) and work/do
#   something on any state


# class Payment(Model):
#     """A payment to an event's provider."""
#
#     # state related fields
#     S_INIT = 'init'
#     S_PAYMENT_DONE = 'payment-done'
#     STATE_CHOICES = (
#         # ... all S_* above ...
#     )
#     state = CharField(choices=STATE_CHOICES)
#
#     # fields with data
#     event = ForeignKey(EventByOrganizer)
#     provider = ForeignKey(Provider)
#     description = CharField(...)
#     invoice = ForeignKey(Invoice)
#     comments = TextField(...)
#     payment_receipt = ImageField(...)
#
#     # fsm is a state machine, each node has:
#     # - the current state (None is special, it's "non created", have all the info
#     #   for the first creation of the instance)
#     # - who needs to work on this state (do something so the flow can progress)
#     # - the next state after all info is supplied (None is special: means "done", "closed")
#     # - all the fields that the user can work/change/use in that state
#     fsm = [
#         (None, ORGZER, S_INIT, [event, provider, description, invoice, comments]),
#         (S_INIT, ADMIN, S_PAYMENT_DONE, [payment_receipt]),
#         (S_PAYMENT_DONE, ORGZER, None, []),
#     ]
#
#
# class Refund(Model):
#     """A refund for organizer expenses during the event."""
#
#     # state related fields
#     S_INIT = 'init'
#     S_PAYMENT_DONE = 'payment-done'
#     STATE_CHOICES = (
#         # ... all S_* above ...
#     )
#     state = CharField(choices=STATE_CHOICES)
#
#     # fields with data
#     event = ForeignKey(EventByOrganizer)
#     to_be_refunded = ForeignKey(Organizer)
#     description = CharField(...)
#     invoices = ManyToMany(Invoice)  # really OneToMany, but this will do
#     comments = TextField(...)
#     payment_receipt = ImageField(...)
#
#     # automatic info
#     total = DecimalField()
#
#     # validations and automatic stuff
#     def save(self):
#         months = {}
#         for invoice in self.invoices:
#             self.total += invoice.amount
#             months.add(invoice.date.month)
#         assert len(months) == 1
#         super().save()
#
#     # fsm is a state machine, each node has:
#     # - the current state (None is special, it's "non created", have all the info
#     #   for the first creation of the instance)
#     # - who needs to work on this state (do something so the flow can progress)
#     # - the next state after all info is supplied (None is special: means "done", "closed")
#     # - all the fields that the user can work/change/use in that state
#     fsm = [
#         (None, ORGZER, S_INIT, [event, provider, description, invoices, comments]),
#         (S_INIT, ADMIN, S_PAYMENT_DONE, [payment_receipt]),
#         (S_PAYMENT_DONE, ORGZER, None, []),
#     ]
#
