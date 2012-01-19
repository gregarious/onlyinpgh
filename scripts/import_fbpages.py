from onlyinpgh.outsourcing.fbpages import PageImportManager, PageImportReport
from onlyinpgh.outsourcing.models import FacebookPage
import logging
importlog = logging.getLogger('onlyinpgh.fb_import')

def import_ids(page_ids):
    page_mgr = PageImportManager()

    importlog.info('Importing Organizations into database from %d pages' % len(page_ids))
    reports = page_mgr.import_orgs(page_ids)    # generator object
    import_count = 0
    for report in reports:
        if report.notices:
            for notice in report.notices:
                if isinstance(notice,PageImportReport.ModelInstanceExists):
                    importlog.info('%s: Record for Organization exists' % report.page_id)
                else:
                    importlog.error('%s: %s' % (report.page_id,unicode(notice)))
        else:
            importlog.info('%s: Imported successfully as %s' % (report.page_id,unicode(report.model_instance)))
            import_count += 1
    importlog.info('%d new Organizations imported' % import_count)

    reports = page_mgr.import_places(page_ids,import_owners=True)    # generator object
    import_count = 0
    for report in reports:
        if report.notices:
            for notice in report.notices:
                if isinstance(notice,PageImportReport.ModelInstanceExists):
                    importlog.info('%s: Record for Place exists' % report.page_id)
                else:
                    importlog.error('%s: %s' % (report.page_id,unicode(notice)))
        else:
            importlog.info('%s: Imported successfully as %s' % (report.page_id,unicode(report.model_instance)))
            import_count += 1
    importlog.info('%d new Places imported' % import_count)

def import_all():
    page_ids = [str(page.fb_id) for page in FacebookPage.objects.filter(ignore=False)]
    import_fbids(page_ids)

def run():
    try:
        importlog.info('Org/Place import start')
        import_all()
        importlog.info('Org/Place import complete')
    except Exception as e:
        importlog.critical('Unexpected error: %s' % str(e))