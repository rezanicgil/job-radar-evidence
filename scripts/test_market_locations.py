"""Check explicit country precedence and conservative fallback on province-only job locations."""
import unittest
from market_inventory import in_turkiye,PROVINCE_NAMES,LOCAL_PROVINCES

class ProvinceLocationTests(unittest.TestCase):
    def test_province_names(self):
        self.assertEqual(len(set(PROVINCE_NAMES)),81)
        self.assertEqual(len(LOCAL_PROVINCES),80)
        for city in ("Eskişehir","ESKISEHIR (hybrid)","Mersin - Remote","Şanlıurfa","KIRIKKALE","Van, Türkiye"):
            with self.subTest(city=city): self.assertTrue(in_turkiye(None,city))
    def test_foreign_and_ambiguous(self):
        for location in ("Van","Van, Texas","Batman Avenue, London","Remote EMEA","Mersin, Germany"):
            with self.subTest(location=location): self.assertFalse(in_turkiye(None,location))
        self.assertFalse(in_turkiye("DE","Mersin"))
        self.assertTrue(in_turkiye(" TUR ","Van"))
if __name__=="__main__":unittest.main()
