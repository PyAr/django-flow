from django.http import HttpResponseRedirect
from django.forms import models as model_forms
from django.urls import reverse_lazy
from django.views.generic.edit import View
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.admin.widgets import RelatedFieldWidgetWrapper
from django.db.models.fields.related import OneToOneRel

from core import models


class HomePage(LoginRequiredMixin, View):

    def get(self, request):
        models_objs = [getattr(models, name) for name in dir(models)]
        all_fsm_models = [
            obj for obj in models_objs
            if isinstance(obj, type) and issubclass(obj, models.FSMModel) and obj is not models.FSMModel]

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

    #def get(self, request, fsmmodel):
    #    print("============= Armar el get del create fsm model!!", fsmmodel)
    #    model = getattr(models, fsmmodel)
    #    step = model.get_step(None, request.user.profile.security_clearance)
    #    form_class = model_forms.modelform_factory(model, fields=step.fields)
    #    print("====== form fact", form_class)
    #    form = form_class()
    #    #for field in form.fields:
    #    #    field['required'] = True
    #    context = {
    #        'form': form,
    #    }
    #    return render(request, 'core/onlyform.html', context=context)

    def get(self, request, fsmmodel, pk=None):
        print("============= Armar el get fsm model!!", fsmmodel, pk)
        model = getattr(models, fsmmodel)
        if pk is None:
            instance_form = None
            current_state = None
        else:
            instance = model.objects.get(pk=pk)
            current_state = instance.state
            form_class = model_forms.modelform_factory(model, fields='__all__')
            instance_form = form_class(instance=instance)
            for field_value in instance_form.fields.values():
                field_value.widget.attrs['disabled'] = True

            # hack
            for field_name, field_value in instance_form.fields.items():
                print("=========== revisando", field_name, type(field_name))
                if field_name == 'invoice':  # FIXME: horrible hack
                    print("============= always new!!!")
                    from core.models import Income
                    from core.admin import admin
                    rel = OneToOneRel(Income.invoice, 'id', 'invoice')
                    instance_form.fields[field_name] = RelatedFieldWidgetWrapper(
                        field_value.widget, rel, admin.admin_site)


        steps = model.get_steps(current_state, request.user.profile.security_clearance)
        context = {'instance_form': instance_form}
        context['forms'] = []
        for step in steps:
            form_class = model_forms.modelform_factory(model, fields=step.fields)
            form = form_class()
            print("====== form fields", form)
            #for field in form.fields:
            #    field['required'] = True
            context['forms'].append(form)
        if pk is None:
            template = 'core/createform.html'
        else:
            template = 'core/updateform.html'
        return render(request, template, context=context)

    def post(self, request, fsmmodel):
        print("================ PPPPOST")
        model = getattr(models, fsmmodel)
        step = model.get_step(None, request.user.profile.security_clearance)
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
