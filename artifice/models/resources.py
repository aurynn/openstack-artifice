from . import Base
from sqlalchemy import Column, String, types, schema, ForeignKey
from sqlalchemy.orm import relationship, backref
# from .tenants import Tenant
from decimal import *

class Resource(Base):

    __tablename__ = "resources"

    id = Column(String, primary_key=True)
    type_ = Column(String)
    tenant_id = Column(String, ForeignKey("tenants.id"), primary_key=True)
    tenant = relationship("Tenant", backref=backref("tenants"))


class BaseModelConstruct(object):

    def __init__(self, raw, start, end):
        # raw is the raw data for this
        self._raw = raw
        self._location = None
        self.start = start
        self.end = end

    @property
    def amount(self):
        return self.size

    def __getitem__(self, item):
        return self._raw[item]

    def get(self, name):
        # Returns a given name value thing?
        # Based on patterning, this is expected to be a dict of usage information
        # based on a meter, I guess?

        return getattr(self, name)

    def _fetch_meter_name(self, name):
        return name

    def usage(self):
        dct = {}
        for meter in self.relevant_meters:
            meter = self._fetch_meter_name(meter)
            try:
                vol = self._raw.meter(meter, self.start, self.end).volume()
                dct[meter] = vol
            except AttributeError:
                # This is OK. We're not worried about non-existent meters,
                # I think. For now, anyway.
                pass
        return dct

    def save(self):
        for meter in self.relevant_meters:
            meter = self._fetch_meter_name(meter)
            try:
                self._raw.meter(meter, self.start, self.end).save()
            except AttributeError:
                # This is OK. We're not worried about non-existent meters,
                # I think. For now, anyway.
                pass


class VM(BaseModelConstruct):
    # The only relevant meters of interest are the type of the interest
    # and the amount of network we care about.
    # Oh, and floating IPs.
    relevant_meters = ["instance:<type>", "network.incoming.bytes", "network.outgoing.bytes"]

    def _fetch_meter_name(self, name):
        if name == "instance:<type>":
            return "instance:%s" % self.type
        return name

    @property
    def amount(self):
        class Amount(object):
            def volume(self):
                return Decimal(1.0)
            def __str__(self):
                return "1.0"
            def __repr__(self):
                return str(self)
        return Amount()

    @property
    def type(self):
        return self._raw["metadata"]["nistance_type"]

    @property
    def size(self):
        return self.type

    @property
    def memory(self):
        return self._raw["metadata"]["memory"]

    @property
    def cpus(self):
        return self._raw["metadata"]["vcpus"]

    @property
    def state(self):
        return self._raw["metadata"]["state"]

    @property
    def bandwidth(self):
        # This is a metered value
        return 0

    @property
    def ips(self):
        """floating IPs; this is a metered value"""
        return 0

    @property
    def name(self):
        return self._raw["metadata"]["display_name"]

class Object(BaseModelConstruct):

    relevant_meters = ["storage.objects.size"]

    type = "object" # object storage

    @property
    def size(self):
        # How much use this had.
        return self._raw.meter("storage.objects.size", self.start, self.end).volume()
        # Size is a gauge measured every 10 minutes.
        # So that needs to be compressed to 60-minute intervals



class Volume(BaseModelConstruct):

    relevant_meters = ["volume.size"]

    @property
    def location(self):
        return self._location

    @property
    def size(self):
        # Size of the thing over time.
        return self._raw.meter("volume.size", self.start, self.end).volume()

class Network(BaseModelConstruct):
    relevant_meters = ["ip.floating"]