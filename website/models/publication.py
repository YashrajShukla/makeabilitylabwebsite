from django.db import models
from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import pre_delete, post_save, m2m_changed, post_delete

from sortedm2m.fields import SortedManyToManyField

from datetime import date, datetime, timedelta
import os

from .person import Person
from .project_umbrella import Project_umbrella
from .keyword import Keyword
from .video import Video
from .talk import Talk
from .poster import Poster

class Publication(models.Model):
    title = models.CharField(max_length=255)
    authors = SortedManyToManyField(Person)
    # authorsOrdered = models.ManyToManyField(Person, through='PublicationAuthorThroughModel')

    # The PDF is required
    pdf_file = models.FileField(upload_to='publications/', null=False, default=None, max_length=255)

    book_title = models.CharField(max_length=255, null=True)
    book_title.help_text = "This is the long-form proceedings title. For example, for UIST, this would be 'Proceedings of the 27th Annual ACM Symposium on User " \
                           "Interface Software and Technology.' For CHI, 'Proceedings of the 2017 CHI Conference on " \
                           "Human Factors in Computing Systems' "
    book_title_short = models.CharField(max_length=255, null=True)
    book_title_short.help_text = "This is a shorter version of book title. For UIST, 'Proceedings of UIST 2014' " \
                           "For CHI, 'Proceedings of CHI 2017'"

    # The thumbnail should have null=True because it is added automatically later by a post_save signal
    # TODO: decide if we should have this be editable=True and if user doesn't add one him/herself, then
    # auto-generate thumbnail
    thumbnail = models.ImageField(upload_to='publications/images/', editable=False, null=True, max_length=255)

    date = models.DateField(null=True)
    num_pages = models.IntegerField(null=True)

    # A publication can be about more than one project
    projects = SortedManyToManyField('Project', blank=True, null=True)
    project_umbrellas = SortedManyToManyField('Project_umbrella', blank=True, null=True)
    keywords = SortedManyToManyField('Keyword', blank=True, null=True)

    # TODO, see if there is an IntegerRangeField or something like that for page_num_start and end
    page_num_start = models.IntegerField(blank=True, null=True)
    page_num_end = models.IntegerField(blank=True, null=True)
    official_url = models.URLField(blank=True, null=True)
    geo_location = models.CharField(max_length=255, blank=True, null=True)
    geo_location.help_text = "The physical location of the conference, if any. For example, CHI 2017 was in 'Denver, Colorado'"

    # Publications can have corresponding videos, talks, posters, etc.
    video = models.OneToOneField(Video, on_delete=models.DO_NOTHING, null=True, blank=True)
    talk = models.ForeignKey(Talk, blank=True, null=True, on_delete=models.DO_NOTHING)
    poster = models.ForeignKey(Poster, blank=True, null=True, on_delete=models.DO_NOTHING)
    code_repo_url = models.URLField(blank=True, null=True)
    code_repo_url.help_text = "URL to github or gitlab"

    series = models.CharField(max_length=255, blank=True, null=True)
    isbn = models.CharField(max_length=255, blank=True, null=True)
    doi = models.CharField(max_length=255, blank=True, null=True)
    publisher = models.CharField(max_length=255, blank=True, null=True)
    publisher_address = models.CharField(max_length=255, blank=True, null=True)
    acmid = models.CharField(max_length=255, blank=True, null=True)

    CONFERENCE = "Conference"
    ARTICLE = "Article"
    JOURNAL = "Journal"
    BOOK_CHAPTER = "Book Chapter"
    BOOK = "Book"
    DOCTORAL_CONSORTIUM = "Doctoral Consortium"
    MS_THESIS = "MS Thesis"
    PHD_DISSERTATION = "PhD Dissertation"
    WORKSHOP = "Workshop"
    POSTER = "Poster"
    DEMO = "Demo"
    WIP = "Work in Progress"
    LATE_BREAKING = "Late Breaking Result"
    PANEL = "Panel"
    OTHER = "Other"

    PUB_VENUE_TYPE_CHOICES = (
        (CONFERENCE, CONFERENCE),
        (ARTICLE, ARTICLE),
        (JOURNAL, JOURNAL),
        (BOOK_CHAPTER, BOOK_CHAPTER),
        (BOOK, BOOK),
        (DOCTORAL_CONSORTIUM, DOCTORAL_CONSORTIUM),
        (MS_THESIS, MS_THESIS),
        (PHD_DISSERTATION, PHD_DISSERTATION),
        (WORKSHOP, WORKSHOP),
        (POSTER, POSTER),
        (DEMO, DEMO),
        (WIP, WIP),
        (LATE_BREAKING, LATE_BREAKING),
        (PANEL, PANEL),
        (OTHER, OTHER)
    )

    # TODO: remove null=True from the following three
    pub_venue_url = models.URLField(blank=True, null=True)
    pub_venue_type = models.CharField(max_length=50, choices=PUB_VENUE_TYPE_CHOICES, null=True)
    extended_abstract = models.NullBooleanField(null=True)
    peer_reviewed = models.NullBooleanField(null=True)

    total_papers_submitted = models.IntegerField(blank=True, null=True)
    total_papers_accepted = models.IntegerField(blank=True, null=True)

    BEST_PAPER_AWARD = "Best Paper Award"
    HONORABLE_MENTION = "Honorable Mention"
    BEST_PAPER_NOMINATION = "Best Paper Nominee"
    TEN_YEAR_IMPACT_AWARD = "10-Year Impact Award"

    AWARD_CHOICES = (
        (BEST_PAPER_AWARD, BEST_PAPER_AWARD),
        (HONORABLE_MENTION, HONORABLE_MENTION),
        (BEST_PAPER_NOMINATION, BEST_PAPER_NOMINATION),
        (TEN_YEAR_IMPACT_AWARD, TEN_YEAR_IMPACT_AWARD)
    )
    award = models.CharField(max_length=50, choices=AWARD_CHOICES, blank=True, null=True)


    def get_person(self):
        """Returns the first author"""
        return self.authors.all()[0]

    def is_extended_abstract(self):
        """Returns True if this publication is an extended abstract"""
        return (self.extended_abstract or
                self.pub_venue_type == self.POSTER or
                self.pub_venue_type == self.DEMO or
                self.pub_venue_type == self.WIP or
                self.pub_venue_type == self.DOCTORAL_CONSORTIUM)

    def get_acceptance_rate(self):
        """Returns the acceptance rate as a percentage"""
        if self.total_papers_accepted and self.total_papers_submitted:
            return 100 * (self.total_papers_accepted / self.total_papers_submitted)
        else:
            return -1

    def is_best_paper(self):
        """Returns true if earned best paper or test of time award"""
        return self.award == self.BEST_PAPER_AWARD or self.award == self.TEN_YEAR_IMPACT_AWARD

    def is_honorable_mention(self):
        """Returns true if earned honorable mention or best paper nomination"""
        return self.award == self.HONORABLE_MENTION or self.award == self.BEST_PAPER_NOMINATION

    def to_appear(self):
        """Returns true if the publication date happens in the future (e.g., tomorrow or later)"""
        return self.date and self.date > date.today()

    def get_citation_as_html(self):
        """Returns a human readable citation as html"""
        citation = ""
        author_idx = 0
        num_authors = self.authors.count()
        for author in self.authors.all():
            citation += author.get_citation_name(full_name=False)

            if (author_idx + 1) < num_authors:
                citation += ", "
            else:
                citation += " "

            author_idx += 1

        citation += "({}). ".format(self.date.year)
        citation += self.title + ". "
        citation += "<i>{}</i>. ".format(self.book_title_short)

        if self.official_url:
            citation += "<a href={}>{}</a>".format(self.official_url, self.official_url)

        return citation

    def get_bibtex_id(self):
        """Generates and returns the bibtex id for this paper"""
        bibtex_id = self.get_person().last_name

        forum = self.book_title_short.lower()
        if "proceedings of" in forum:
            forum = forum.replace('proceedings of', '')

        forum = forum.upper().replace(" ", "")
        if not forum[-1].isdigit():
            forum = forum + str(self.date.year)

        bibtex_id += ":" + forum

        # code to make acronym from: https://stackoverflow.com/a/4355337
        title_acronym = ''.join(w[0] for w in self.title.split() if w[0].isupper())
        bibtex_id += ":" + title_acronym[:3]

        if self.doi:
            doi = self.doi.rsplit('/', 1)[-1]
            bibtex_id += doi

        bibtex_id += ","

        return bibtex_id


    def get_citation_as_bibtex(self, newline="<br/>", use_hyperlinks=True):
        """Returns bibtex citation as a string"""
        bibtex = ""

        if self.pub_venue_type is self.JOURNAL or\
            self.pub_venue_type is self.ARTICLE:
            bibtex += "@article{"
        else:
            bibtex += "@inproceedings{"


        bibtex += self.get_bibtex_id() + newline

        # start author block
        bibtex += " author = {"

        author_idx = 0
        num_authors = self.authors.count()
        for author in self.authors.all():
            citation_name = author.get_citation_name(full_name=True)
            bibtex += citation_name

            if (author_idx + 1) < num_authors:
                bibtex += " and "

            author_idx += 1
        bibtex += "}" + newline
        # end author block

        bibtex += " title={{{}}},{}".format(self.title, newline)
        bibtex += " booktitle={{{}}},{}".format(self.book_title, newline)
        bibtex += " booktitleshort={{{}}},{}".format(self.book_title_short, newline)

        if self.series:
            bibtex += " series = {" + self.series + "},"

        bibtex += " year={{{}}},{}".format(self.date.year, newline)

        if self.isbn:
            bibtex += " isbn={{{}}},{}".format(self.isbn, newline)

        if self.geo_location:
            bibtex += " location={{{}}},{}".format(self.geo_location, newline)

        if self.page_num_start and self.page_num_end:
            bibtex += " pages={{{}--{}}},{}".format(self.page_num_start, self.page_num_end, newline)

        if self.num_pages:
            bibtex += " numpages={{{}}},{}".format(self.num_pages, newline)

        if self.doi:
            if use_hyperlinks:
                bibtex += " doi={{<a href='{}'>{}</a>}},{}".format(self.doi, self.doi, newline)
            else:
                bibtex += " doi={{{}}},{}".format(self.doi, newline)

        if self.official_url:
            if use_hyperlinks:
                bibtex += " url={{<a href='{}'>{}</a>}},{}".format(self.official_url, self.official_url, newline)
            else:
                bibtex += " url={{{}}},{}".format(self.official_url, newline)

        if self.acmid:
            bibtex += " acmid={{{}}},{}".format(self.acmid, newline)

        if self.publisher:
            bibtex += " publisher={{{}}},{}".format(self.publisher, newline)

        bibtex += "}"
        return bibtex

    def __str__(self):
        return self.title


def update_file_name_publication(sender, instance, action, reverse, **kwargs):
    # Reverse: Indicates which side of the relation is updated (i.e., if it is the forward or reverse relation that is being modified)
    # Action: A string indicating the type of update that is done on the relation.
    # post_add: Sent after one or more objects are added to the relation
    if action == 'post_add' and not reverse:
        initial_path = instance.pdf_file.path
        person = instance.get_person()
        name = person.last_name
        year = instance.date.year
        title = ''.join(x for x in instance.title.title() if not x.isspace())
        title = ''.join(e for e in title if e.isalnum())

        # Get the publication venue but remove proceedings from it (if it exists)
        forum = instance.book_title_short.lower()
        if "proceedings of" in forum.lower():
            forum = forum.replace('proceedings of', '')

        forum = forum.strip().upper()
        forum = ''.join(x for x in forum if not x.isspace())

        if not forum[-1].isdigit():
            forum = forum + str(year)

        #change the path of the pdf file to point to the new file name
        instance.pdf_file.name = os.path.join('publications', name + '_' + title + '_' + forum + '.pdf')
        new_path = os.path.join(settings.MEDIA_ROOT, instance.pdf_file.name)
        os.rename(initial_path, new_path)
        instance.save()

m2m_changed.connect(update_file_name_publication , sender=Publication.authors.through)

@receiver(pre_delete, sender=Publication)
def publication_delete(sender, instance, **kwards):
    if instance.thumbnail:
        instance.thumbnail.delete(True)
    if instance.pdf_file:
        instance.pdf_file.delete(True)
    if instance.thumbnail:
        instance.thumbnail.delete(True)