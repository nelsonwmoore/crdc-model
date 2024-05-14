"""Use caDSR API to get CRDC data elements and save to MDF files."""

from __future__ import annotations

import requests
from bento_mdf.mdf import MDF
from bento_meta.model import Model
from bento_meta.objects import Node, Property, Term


class CRDCDataElements:
    """CRDC data elements."""

    def __init__(self) -> None:
        """Post-initialization operations."""
        self.data_elements: list[dict[str, str | list[dict[str, str | None]]]] = (
            self.fetch_data_elements()
        )
        self.model = Model(handle="CRDC")
        self.get_nodes_from_data_elements()
        self.mdf = MDF(model=self.model)

    def fetch_data_elements(self) -> list[dict[str, str | list[dict[str, str | None]]]]:
        """Get data elements from JSON response."""
        response = requests.get(
            "https://cadsrapi.cancer.gov/rad/NCIAPI/1.0/api/DataElement/getCRDCList",
            headers={"accept": "application/json"},
            timeout=10,
        )
        json_response = response.json()
        return json_response.get("CRDCDataElements")

    def get_data_element_keys(self) -> dict[str, int]:
        """Get keys and counts from JSON response."""
        return {
            de_key: sum(1 for de in self.data_elements if de_key in de)
            for de_key in {key for de in self.data_elements for key in de}
        }

    def get_prop_terms_from_data_element(
        self,
        prop: Property,
        de: dict[str, str | list[dict[str, str | None]]],
    ) -> None:
        """Add a property's permissible values to model from data element."""
        terms = [
            Term(
                {
                    "value": pv.get("Permissible Value"),
                    "origin_id": pv.get("VM Public ID"),
                    "origin_definition": pv.get("VM Description"),
                    "origin_name": "caDSR",
                },
            )
            for pv in de.get("permissibleValues", [])
            if isinstance(pv, dict)
        ]
        self.model.add_terms(prop, *terms)

    def calc_value_domain_from_de(
        self,
        de: dict[str, str | list[dict[str, str | None]]],
    ) -> str:
        """Calculate value domain from data element."""
        # for now, value_domain only provided as "Enumerated" or "Non-enumerated"
        if de.get("VD Type") == "Enumerated":
            return "value_set"
        return "TBD"

    def get_node_props_from_data_element(
        self,
        node: Node,
        de: dict[str, str | list[dict[str, str | None]]],
    ) -> None:
        """Add a node's properties (with term annoations) to model from data element."""
        prop = Property(
            {
                "handle": de.get("CRDC Name"),
                "model": "CRDC",
                "value_domain": self.calc_value_domain_from_de(de),
                "desc": de.get("CRDC Definition"),
            },
        )
        term_annotation = Term(
            {
                "value": de.get("CRDC Name"),
                "origin_id": de.get("CDE Public ID"),
                "origin_definition": de.get("CRDC Definition"),
                "origin_version": de.get("Version"),
                "origin_name": "caDSR",
            },
        )
        self.model.add_prop(node, prop)
        self.model.annotate(prop, term_annotation)
        if de.get("VD Type") == "Enumerated":
            self.get_prop_terms_from_data_element(prop, de)

    def get_nodes_from_data_elements(self) -> None:
        """Add nodes to model from data elements."""
        for de in self.data_elements:
            node_hdl = de.get("CRD Domain", "TBD")
            if node_hdl not in self.model.nodes:
                node = Node({"handle": node_hdl})
                self.model.add_node(node)
            else:
                node = self.model.nodes[node_hdl]
            self.get_node_props_from_data_element(node, de)


if __name__ == "__main__":
    crdc_data_elements = CRDCDataElements()
    crdc_data_elements.mdf.write_mdf(file="model-desc/crdc-model.yml")
