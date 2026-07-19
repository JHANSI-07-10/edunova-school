from rest_framework import viewsets, mixins, generics
from rest_framework.permissions import AllowAny
from .models import (
    SchoolSettings, Campus, AcademicProgram, Department, LeadershipMember,
    SchoolStat, WhyChooseItem, TechnologyPartner, CMSPage, NewsPost, Event,
    GalleryAlbum, GalleryImage, Achievement, Testimonial, FAQ, Document,
    JobPosting, JobApplication, InterviewSchedule, ContactSubmission, ScholarshipInfo,
)
from . import serializers as ser


class SchoolSettingsViewSet(viewsets.ReadOnlyModelViewSet):
    """Singleton — frontend calls /api/cms/settings/1/ or /api/cms/settings/ and takes first result."""
    queryset = SchoolSettings.objects.all()
    serializer_class = ser.SchoolSettingsSerializer


class CampusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Campus.objects.all()
    serializer_class = ser.CampusSerializer


class AcademicProgramViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AcademicProgram.objects.all()
    serializer_class = ser.AcademicProgramSerializer


class DepartmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Department.objects.all()
    serializer_class = ser.DepartmentSerializer


class LeadershipMemberViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LeadershipMember.objects.all()
    serializer_class = ser.LeadershipMemberSerializer


class SchoolStatViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SchoolStat.objects.all()
    serializer_class = ser.SchoolStatSerializer


class WhyChooseItemViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WhyChooseItem.objects.all()
    serializer_class = ser.WhyChooseItemSerializer


class TechnologyPartnerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TechnologyPartner.objects.all()
    serializer_class = ser.TechnologyPartnerSerializer


class CMSPageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CMSPage.objects.all()
    serializer_class = ser.CMSPageSerializer
    lookup_field = "slug"


class NewsPostViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NewsPost.objects.filter(is_published=True)
    serializer_class = ser.NewsPostSerializer
    lookup_field = "slug"


class EventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Event.objects.all()
    serializer_class = ser.EventSerializer


class GalleryAlbumViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GalleryAlbum.objects.all()
    serializer_class = ser.GalleryAlbumSerializer


class GalleryImageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GalleryImage.objects.all()
    serializer_class = ser.GalleryImageSerializer


class AchievementViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Achievement.objects.all()
    serializer_class = ser.AchievementSerializer


class TestimonialViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Testimonial.objects.filter(is_featured=True)
    serializer_class = ser.TestimonialSerializer


class FAQViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FAQ.objects.all()
    serializer_class = ser.FAQSerializer


class DocumentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ser.DocumentSerializer

    def get_queryset(self):
        qs = Document.objects.all()
        audience = self.request.query_params.get("audience")
        if audience:
            qs = qs.filter(audience=audience)
        return qs


class JobPostingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = JobPosting.objects.filter(is_open=True)
    serializer_class = ser.JobPostingSerializer


class JobApplicationCreateView(generics.CreateAPIView):
    queryset = JobApplication.objects.all()
    serializer_class = ser.JobApplicationSerializer
    permission_classes = [AllowAny]


class ScholarshipInfoViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = ScholarshipInfo.objects.all()
    serializer_class = ser.ScholarshipInfoSerializer


class ContactSubmissionViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Public: write-only. Contact page POSTs here; nothing is exposed to read publicly."""
    queryset = ContactSubmission.objects.all()
    serializer_class = ser.ContactSubmissionSerializer
