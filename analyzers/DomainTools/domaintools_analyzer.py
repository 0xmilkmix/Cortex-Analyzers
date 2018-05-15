#!/usr/bin/env python
# encoding: utf-8

from domaintools.exceptions import NotFoundException
from domaintools.exceptions import NotAuthorizedException
from domaintools.exceptions import ServiceUnavailableException


from domaintools import API


from cortexutils.analyzer import Analyzer


class DomainToolsAnalyzer(Analyzer):

    def __init__(self):
        Analyzer.__init__(self)
        self.service = self.get_param(
            'config.service', None, 'Service parameter is missing')

    def domaintools(self, data):
        """

        :param service:
        :return:
        """
        if (self.service == 'reverse-ip' and self.data_type == 'ip'):
            self.service = 'host-domains'

        api = API(self.get_param('config.username'), self.get_param('config.key'))

        if self.service == 'reverse-ip' and self.data_type in ['domain', 'ip', 'fqdn']:
            response = api.reverse_ip(data).response()

        elif self.service == 'host-domains' and self.data_type == 'ip':
            response = api.host_domains(data).response()

        elif self.service == 'name-server-domains' and self.data_type == 'domain':
            response = api.reverse_name_server(data).response()

        elif self.service == 'whois/history' and self.data_type == 'domain':
            response = api.whois_history(data).response()

        elif self.service == 'whois/parsed' and self.data_type == 'domain':
            response = api.parsed_whois(data).response()

        elif self.service == 'reverse-whois':
            response = api.reverse_whois(data, mode='purchase').response()

        elif self.service == 'whois' and self.data_type == 'ip':
            response = api.whois(data).response()

        return response


    def summary(self, raw):
        r = {
            "service": self.service,
            "dataType": self.data_type
        }

        if "ip_addresses" in raw:
            if type(raw["ip_addresses"]) == dict:
                r["ip"] = {
                    "address": raw["ip_addresses"]["ip_address"],
                    "domain_count": raw["ip_addresses"]["domain_count"]
                }
            elif type(raw["ip_addresses"]) == list:
                r["ip"] = {
                    "address": "{} IP addresses".format(len(r)),
                    "domain_count": sum(d["domain_count"] for d in raw["ip_addresses"])
                }

        if "domain_count" in raw:
            r["domain_count"] = {
                "current": raw["domain_count"]["current"],
                "historic": raw["domain_count"]["historic"]
            }

        if "registrant" in raw:
            r["registrant"] = raw["registrant"]
        elif "response" in raw and "registrant" in raw["response"]:
            r["registrant"] = raw["response"]["registrant"]

        if "parsed_whois" in raw:
            r["registrar"] = raw["parsed_whois"]["registrar"]["name"]
            #

        if "name_server" in raw:
            r["name_server"] = raw["name_server"]["hostname"]
            r["domain_count"] = raw["name_server"]["total"]

        taxonomies = []

        # Prepare predicate and value for each service
        if r["service"] in ["reverse-ip", "host-domains"]:
            taxonomies.append(self.build_taxonomy("info", "DT", "Reverse_IP",
                                                  "\"{}, {} domains\"".format(r["ip"]["address"],
                                                                              r["ip"]["domain_count"])))

        if r["service"] == "name-server-domains":
            taxonomies.append(self.build_taxonomy("info", "DT", "Reverse_Name_Server",
                                                  "\"{}, {} domains\"".format(r["name_server"], r["domain_count"])))

        if r["service"] == "reverse-whois":
            taxonomies.append(self.build_taxonomy("info", "DT", "Reverse_Whois",
                                                  "\"curr:{} / hist:{} domains\"".format(r["domain_count"]["current"],
                                                                                         r["domain_count"][
                                                                                             "historic"])))

        if r["service"] == "whois/history":
            taxonomies.append(self.build_taxonomy("info", "DT", "Whois_History",
                                                  "\"{}, {} domains \"".format(r["name_server"], r["domain_count"])))

        if r["service"] == "whois/parsed" or r['service'] == "whois":
            if r["registrar"]:
                taxonomies.append(self.build_taxonomy("info", "DT", "Whois", "\"REGISTRAR:{}\"".format(r["registrar"])))
            if r["registrant"]:
                taxonomies.append(
                    self.build_taxonomy("info", "DT", "Whois", "\"REGISTRANT:{}\"".format(r["registrant"])))

        result = {'taxonomies': taxonomies}
        return result

    def run(self):
        data = self.get_data()

        try:
            r = self.domaintools(data)

            if 'response' in r:
                self.report(r.get('response'))
            elif 'error' in r and 'message' in r['error']:
                self.error(r['error']['message'])
            else:
                self.report(r)

        except NotFoundException:
            self.error(self.data_type.capitalize() + " not found")
        except NotAuthorizedException:
            self.error("An authorization error occurred")
        except ServiceUnavailableException:
            self.error("DomainTools Service is currenlty unavailable")
        except Exception as e:
            self.unexpectedError(e)

        else:
            self.error('Unknown DomainTools service or invalid data type')


if __name__ == '__main__':
    DomainToolsAnalyzer().run()
