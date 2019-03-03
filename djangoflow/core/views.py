from django.http import HttpResponseRedirect
from django.forms import models as model_forms
from django.urls import reverse_lazy
from django.views.generic.edit import View
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin

from core import models


class HomePage(LoginRequiredMixin, View):

    def get(self, request):
        models_objs = [getattr(models, name) for name in dir(models)]
        all_fsm_models = []
        for obj in models_objs:
            if obj is models.FSMModel:
                continue
            if isinstance(obj, type) and issubclass(obj, models.FSMModel):
                all_fsm_models.append(obj)

        # add create stuff
        create_context = []
        for model in all_fsm_models:
            if request.user.profile.security_clearance in model.get_create_roles():
                model_name = model.__name__
                create_context.append({
                    'text': "Create new {}".format(model_name),
                    'url': reverse_lazy(
                        'create_flow', kwargs={'fsmmodel': model_name}),
                })

        # add open stuff
        open_context = []
        for model in all_fsm_models:
            alive_instances = model.objects.exclude(state=model.fsm_final_state).all()
            for instance in alive_instances:
                instance_current_steps = instance.get_current_steps(
                    request.user.profile.security_clearance)
                if instance_current_steps:
                    model_name = model.__name__
                    open_context.append({
                        'text': "Work on {} in state {}".format(instance, instance.state),
                        'url': reverse_lazy(
                            'update_flow', kwargs={'fsmmodel': model_name, 'pk': instance.pk}),
                    })

        context = {'create': create_context, 'open': open_context}
        return render(request, 'core/basic_create_list.html', context=context)


class CreateFSMModel(View):

    def get(self, request, fsmmodel, pk=None):
        print("============= Armar el get fsm model!!", fsmmodel, pk)
        model = getattr(models, fsmmodel)
        if pk is None:
            instance_form = None
            current_state = None
            instance_pk = None
        else:
            instance = model.objects.get(pk=pk)
            instance_pk = instance.pk
            current_state = instance.state
            form_class = model_forms.modelform_factory(model, fields='__all__')
            instance_form = form_class(instance=instance)
            for field_value in instance_form.fields.values():
                field_value.widget.attrs['disabled'] = True

            # # hack
            # for field_name, field_value in instance_form.fields.items():
            #     print("=========== revisando", field_name, type(field_name))
            #     if field_name == 'invoice':  # FIXME: horrible hack
            #         print("============= always new!!!")
            #         from core.models import Income
            #         from core.admin import admin
            #         rel = OneToOneRel(Income.invoice, 'id', 'invoice')
            #         instance_form.fields[field_name] = RelatedFieldWidgetWrapper(
            #             field_value.widget, rel, admin.admin_site)

        steps = model.get_steps(current_state, request.user.profile.security_clearance)
        context = {'instance_form': instance_form}
        context['forms'] = []
        for step in steps:
            form_class = model_forms.modelform_factory(model, fields=step.fields)
            form = form_class()
            model_name = model.__name__
            url_kwargs = {'fsmmodel': model_name, 'pk': instance_pk, 'step_index': step.index}
            context['forms'].append({
                'form': form,
                'url': reverse_lazy('post_flow', kwargs=url_kwargs),
            })
        if pk is None:
            template = 'core/createform.html'
        else:
            template = 'core/updateform.html'
        return render(request, template, context=context)

    def post(self, request, fsmmodel, step_index, pk):
        print("================ PPPPOST", fsmmodel, step_index, pk)
        model = getattr(models, fsmmodel)
        step = model.get_step_by_index(int(step_index))
        form_class = model_forms.modelform_factory(model, fields=step.fields)
        form = form_class(request.POST)
        assert form.is_valid()  # FIXME: be polite
        obj = form.save(commit=False)
        obj.state = step.next_state
        obj.save()
        return HttpResponseRedirect(reverse_lazy('home'))


class MagicPapota(View):

    def get(self, request):
        pass

    def post(self, request):
        pass
