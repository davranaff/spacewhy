import {
  DASHBOARD_TEMPLATES,
  DASHBOARD_TEMPLATE_SECTIONS,
  filterDashboardTemplates,
  getDashboardTemplate,
} from './dashboard-template-data';

describe('dashboard template inventory', () => {
  it('mirrors all 41 web dashboard routes without duplicate ids', () => {
    expect(DASHBOARD_TEMPLATES).toHaveLength(41);
    expect(new Set(DASHBOARD_TEMPLATES.map(template => template.id)).size).toBe(
      41,
    );
  });

  it('keeps every template reachable from exactly one section', () => {
    const sectionIds = DASHBOARD_TEMPLATE_SECTIONS.flatMap(section =>
      section.templates.map(template => template.id),
    );

    expect(sectionIds).toHaveLength(41);
    expect(new Set(sectionIds).size).toBe(41);
  });

  it('supports lookup and family/path search', () => {
    expect(getDashboardTemplate('invoice-edit')?.kind).toBe('form');
    expect(filterDashboardTemplates('booking-overview')).toHaveLength(1);
    expect(filterDashboardTemplates('/dashboard/product')).toHaveLength(4);
  });
});
