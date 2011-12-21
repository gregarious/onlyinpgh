from django.test import TestCase

class FBOrganizationInsertion(TestCase):
    def test_fb_new_org(self):
        '''
        Tests that a truly new org is inserted correctly.
        '''
        self.fail('not yet implemented')

    def test_fb_existing_org(self):
        '''
        Tests that an org is not created if an existing org already exists.
        '''
        self.fail('not yet implemented')

    def test_fb_bad_org(self):
        '''
        Tests that a nonexistant or user FB page insertion attempt fails gracefully.
        '''
        # TODO: ensure user pages don't get inserted
        self.fail('not yet implemented')