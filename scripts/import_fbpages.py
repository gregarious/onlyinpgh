from onlyinpgh.outsourcing.fbpages import PageImportManager, PageImportReport
from onlyinpgh.outsourcing.models import FacebookPage
import logging, json
importlog = logging.getLogger('onlyinpgh.fb_import')

def import_ids(page_ids):
    page_mgr = PageImportManager()
    importlog.info('Pulling %d pages from Facebook' % len(page_ids))
    
    importlog.info('Importing Organizations into database from %d pages' % len(page_ids))
    page_infos = page_mgr.pull_page_info(page_ids)    # cache pages
    
    importlog.info('Refresing cached FB page infos')
    for pid,info in zip(page_ids,page_infos):
        if not isinstance(info,dict):
            importlog.info('Cannot store page info JSON for fb id %s' % str(pid))
            continue
        info.pop('metadata',None)       # don't need to store metadata if it exists
        record, _ = FacebookPage.objects.get_or_create(fb_id=pid)
        record.pageinfo_json = json.dumps(info)
        record.save()

    import_count = 0
    for pid in page_ids:
        report = page_mgr.import_org(pid)
        if report.notices:
            for notice in report.notices:
                if isinstance(notice,PageImportReport.ModelInstanceExists):
                    importlog.info('%s: Record for Organization exists' % report.page_id)
                else:
                    importlog.error('%s: %s' % (report.page_id,unicode(notice)))
        else:
            importlog.info('%s: Imported successfully as %s (id=%d)' % (report.page_id,
                                                                        unicode(report.model_instance),
                                                                        report.model_instance.id))
            import_count += 1
    importlog.info('%d new Organizations imported' % import_count)

    reports = page_mgr.import_place(page_ids,import_owners=True)    # generator object
    import_count = 0
    for pid in page_ids:
        report = page_mgr.import_place(pid)
        if report.notices:
            for notice in report.notices:
                if isinstance(notice,PageImportReport.ModelInstanceExists):
                    importlog.info('%s: Record for Place exists' % report.page_id)
                else:
                    importlog.error('%s: %s' % (report.page_id,unicode(notice)))
        else:
            importlog.info('%s: Imported successfully as %s (id=%d)' % (report.page_id,
                                                                        unicode(report.model_instance),
                                                                        report.model_instance.id))
            import_count += 1
    importlog.info('%d new Places imported' % import_count)

def import_all():
    page_ids = [str(page.fb_id) for page in FacebookPage.objects.filter(ignore=False)]
    import_fbids(page_ids)

def import_pageinfos():
    all_page_ids = [str(page.fb_id) for page in FacebookPage.objects.filter(pageinfo_json='')]
    page_mgr = PageImportManager()

    offset, step_size = 0, 2000
    importlog.info('Pulling %d pages from Facebook (step of %d)' % (len(all_page_ids),step_size))    
    while offset < len(all_page_ids):
        page_ids = all_page_ids[offset:min(offset+step_size,len(all_page_ids)-1)]
        infos = page_mgr.pull_page_info(page_ids)
        importlog.info('Importing %d page infos into database' % len(page_ids))
        
        for pid,info in zip(page_ids,infos):
            if not isinstance(info,dict):
                importlog.info('Bad response for page id %s' % str(pid))
                continue
            info.pop('metadata',None)
            record = FacebookPage.objects.get(fb_id=pid)
            record.pageinfo_json = json.dumps(info)
            record.save()
        offset += step_size

def run():
    try:
        importlog.info('PageInfo import start')
        import_pageinfos()
        importlog.info('PageInfo import complete')
        # importlog.info('Org/Place import start')
        # import_all()
        # importlog.info('Org/Place import complete')
    except Exception as e:
        importlog.critical('Unexpected error: %s' % str(e))